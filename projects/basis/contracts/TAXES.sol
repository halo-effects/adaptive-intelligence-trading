/*
 * SPDX-License-Identifier: None
 */

pragma solidity 0.8.24;

// IERC20 interface with necessary functions
interface IERC20 {
    function hybridMultiplier() external view returns (uint256);
    function DEV() external view returns (address);
    function hasBonded() external view returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function sellTokens(uint256 amount, address recipient) external returns (uint256);
    function InjectUSDC(uint256 amount) external;
    function addToRewards(uint256 amount) external;
}

interface IPREDICTION{
    function donate(address marketToken, uint256 amount, bool isBounty) external;
}

interface ISTAKING{
    function injectYield(uint256 _amount) external;
}

contract ATaxes {
    address public CEO;
    IERC20 private MAINTOKEN; // Reference to MAINTOKEN
    ISTAKING private STAKING;
    IERC20 private USDC; 
    
    // Tax rate variables initialized with values from ASwap
    uint256 public _taxRateStasis = 50;
    uint256 public _taxRateStable = 50;
    uint256 public _taxRateDefault = 150;
    uint256 public _taxRatePrediction = 150;
    uint256 public injectRate = 16;    
    uint256 public devRate = 20;
    uint256 public presaleRate = 4;    

    // DEV fee sharing system
    uint256 private constant MAX_SHARES = 10;
    uint256 private constant TOTAL_BASIS_POINTS = 10000;

    mapping(address => mapping(address => uint256)) public devBasisPoints; // token => wallet => basisPoints
    mapping(address => address[]) public devWallets; // token => list of wallets with >0 basisPoints
    mapping(address => uint256) public devTotalAllocated; // token => total basisPoints allocated (<=10000)
    mapping(address => bool) public isWhitelisted; // Whitelist for DEX transactions
    mapping(address => bool) public isPrediction; // Whitelist for DEX transactions

    // DEV fee earnings tracking
    mapping(address => uint256) public totalDevTaxCollected; // token => total USDC collected as devTax for that token
    mapping(address => uint256) public devTotalEarnings; // recipient => total USDC earned across all tokens (DEV or shared wallets)
    mapping(address => mapping(address => uint256)) public tokenDevEarnings; // token => recipient => USDC earned from that token (DEV or shared wallets)
    
    // Surge tax time-based system
    uint256 private constant THIRTY_DAYS = 30 days;
    uint256 private constant SEVEN_DAYS = 7 days;
    uint256 private constant ONE_HOUR = 1 hours;

    struct Surge {
        uint256 start;
        uint256 dur;
    }

    mapping(address => Surge[]) public surgeHistory;
    mapping(address => uint256) public surgeStartTime;
    mapping(address => uint256) public surgeDuration;
    mapping(address => uint256) public surgeStartRate;
    mapping(address => uint256) public surgeEndRate;
    mapping(address => bool) public isSurgeActive;

    // Events
    event SurgeStarted(address indexed token, uint256 startRate, uint256 endRate, uint256 duration, uint256 startTime);
    event SurgeEnded(address indexed token, uint256 refundSeconds);
    event DevTaxDistributed(address indexed token, address indexed recipient, uint256 amount);

    // Access control modifier
    modifier onlyCEO() {
        require(msg.sender == CEO, "Only CEO");
        _;
    }

    // Constructor to set MAINTOKEN, USDC, NFT, PREDICTION and CEO
    constructor(address mainToken, address staking, address _usdc) {
        CEO = msg.sender;
        MAINTOKEN = IERC20(mainToken);
        STAKING = ISTAKING(staking);
        USDC = IERC20(_usdc);
    }

    function setPrediction(address prediction) external onlyCEO {        
        bool value = !isPrediction[prediction];
        isPrediction[prediction] = value;
        isWhitelisted[prediction] = value;
    }

    function setWhitelistStatus(address user, bool value) external onlyCEO {
        require(user != address(0), "cannot whitelist null address");
        isWhitelisted[user] = value;
    }

    function setMain(address _mainToken) external onlyCEO {
        MAINTOKEN = IERC20(_mainToken);
    }

    function setStaking(address _staking) external onlyCEO {
        STAKING = ISTAKING(_staking);
    }

    function setTaxRates(uint256 buyback, uint256 presalers, uint256 dev) external onlyCEO {
        require(dev >= 15 && dev <= 40, "Dev rate out of range [15-40]");
        require(buyback >= 0 && buyback <= 20, "Buyback rate out of range [0-20]");
        require(presalers >= 2 && presalers <= 10, "Presalers rate out of range [2-10]");

        uint256 sumNonNft = buyback + presalers + dev;
        require(sumNonNft <= 70, "Sum of non-NFT rates too high (max 70 to leave >=30% for NFT)");

        injectRate = buyback;
        presaleRate = presalers;
        devRate = dev;
    }

    function setTaxesStable(uint256 newTaxRate) external onlyCEO {
        require(newTaxRate <= 200, "Cannot raise above 2%");
        _taxRateStable = newTaxRate;
    }

    function setTaxesDefault(uint256 newTaxRate) external onlyCEO {
        require(newTaxRate <= 200, "Cannot raise above 2%");
        _taxRateDefault = newTaxRate;
    }

    function setTaxesStasis(uint256 newTaxRate) external onlyCEO {
        require(newTaxRate <= 200, "Cannot raise above 2%");
        _taxRateStasis = newTaxRate;
    }

    function startSurgeTax(uint256 startRate, uint256 endRate, uint256 duration, address token) external {
        IERC20 TOKEN = IERC20(token);
        require(TOKEN.DEV() == msg.sender, "only dev");
        uint256 multiplier = TOKEN.hybridMultiplier();
        require(multiplier >= 1 && (multiplier <= 90 || multiplier == 100), "invalid multiplier");

        uint256 maxRate;
        if (multiplier == 100) {
            maxRate = 50;
        } else {
            uint256 decrement = (multiplier - 1) * 1400 / 89;  // Base decrement
            uint256 rawMax = 1500 - decrement;
            uint256 step = 50;

            maxRate = (rawMax / step) * step;
            maxRate = maxRate < 100 ? 100 : maxRate;
        }

        require(startRate <= maxRate && startRate >= 10, "invalid start rate");
        require(endRate <= startRate && endRate >= 0, "invalid end rate");
        require(duration >= ONE_HOUR, "duration too short");

        _pruneHistory(token);
        uint256 currentUsed = _calculateUsed(token);
        require(currentUsed + duration <= SEVEN_DAYS, "quota exceeded");
        require(!isSurgeActive[token], "surge already active");

        surgeStartTime[token] = block.timestamp;
        surgeDuration[token] = duration;
        surgeStartRate[token] = startRate;
        surgeEndRate[token] = endRate;
        isSurgeActive[token] = true;
        surgeHistory[token].push(Surge({start: block.timestamp, dur: duration}));

        emit SurgeStarted(token, startRate, endRate, duration, block.timestamp);
    }

    function endSurgeTax(address token) external {
        IERC20 TOKEN = IERC20(token);
        require(TOKEN.DEV() == msg.sender, "only dev");
        require(isSurgeActive[token], "not active");

        uint256 start = surgeStartTime[token];
        uint256 dur = surgeDuration[token];
        uint256 elapsed = block.timestamp - start;
        if (elapsed >= dur) {
            isSurgeActive[token] = false;
            emit SurgeEnded(token, 0);
            return;
        }

        uint256 remaining = dur - elapsed;
        uint256 refundHours = remaining / 3600;
        uint256 refund = refundHours * 3600;
        uint256 burned = remaining - refund;

        surgeDuration[token] = elapsed + burned;
        surgeHistory[token][surgeHistory[token].length - 1].dur = elapsed + burned;
        isSurgeActive[token] = false;

        _pruneHistory(token);

        emit SurgeEnded(token, refund);
    }

    // View available surge quota
    function availableSurgeQuota(address token) public view returns (uint256) {
        return SEVEN_DAYS - _calculateUsed(token);
    }

    // Internal: Prune old history
    function _pruneHistory(address token) internal {
        Surge[] storage history = surgeHistory[token];
        uint256 i = 0;
        while (i < history.length) {
            if (history[i].start + history[i].dur < block.timestamp - THIRTY_DAYS) {
                history[i] = history[history.length - 1];
                history.pop();
            } else {
                i++;
            }
        }
    }

    // Internal: Calculate used quota in last 30 days
    function _calculateUsed(address token) internal view returns (uint256) {
        Surge[] storage history = surgeHistory[token];
        uint256 used = 0;
        uint256 windowStart = block.timestamp - THIRTY_DAYS;
        for (uint256 i = 0; i < history.length; i++) {
            uint256 pStart = history[i].start;
            uint256 pEnd = pStart + history[i].dur;
            uint256 startOverlap = pStart > windowStart ? pStart : windowStart;
            uint256 endOverlap = pEnd < block.timestamp ? pEnd : block.timestamp;
            if (startOverlap < endOverlap) {
                used += endOverlap - startOverlap;
            }
        }
        return used;
    }

    // Consolidated getter function for tax rates
    function getTaxRate(IERC20 token, address user) public view returns (uint256) {
        if (isWhitelisted[user]) {
            return 0;
        }

        if (address(token) == address(MAINTOKEN)) {
            return _taxRateStasis;
        }

        address dev = token.DEV();
        if(isPrediction[dev]){
            return _taxRatePrediction;
        }

        uint256 surge = getCurrentSurgeTax(address(token));
        if (token.hybridMultiplier() == 100) {
            return _taxRateStable + surge;
        }
        return _taxRateDefault + surge;
    }

    // Get current degraded surge tax
    function getCurrentSurgeTax(address token) public view returns (uint256) {
        if (!isSurgeActive[token] || block.timestamp >= surgeStartTime[token] + surgeDuration[token]) {
            return 0;
        }
        uint256 elapsed = block.timestamp - surgeStartTime[token];
        uint256 totalDrop = surgeStartRate[token] - surgeEndRate[token];
        uint256 currentDrop = (elapsed * totalDrop) / surgeDuration[token];
        return surgeStartRate[token] - currentDrop;
    }

    // Add a DEV share for a token
    function addDevShare(IERC20 token, address wallet, uint256 basisPoints) external {
        address tokenAddr = address(token);
        require(tokenAddr != address(MAINTOKEN), "Cannot set for MAINTOKEN");
        require(msg.sender == token.DEV(), "Only DEV can add shares");
        require(wallet != address(0), "Invalid wallet");
        require(basisPoints > 0, "Basis points must be >0");

        uint256 oldBp = devBasisPoints[tokenAddr][wallet];
        uint256 newTotal = devTotalAllocated[tokenAddr] - oldBp + basisPoints;
        require(newTotal <= TOTAL_BASIS_POINTS, "Exceeds 100%");

        if (oldBp == 0) {
            require(devWallets[tokenAddr].length < MAX_SHARES, "Max 10 shares");
            devWallets[tokenAddr].push(wallet);
        }

        devBasisPoints[tokenAddr][wallet] = basisPoints;
        devTotalAllocated[tokenAddr] = newTotal;
    }

    // Remove a DEV share for a token
    function removeDevShare(IERC20 token, address wallet) external {
        address tokenAddr = address(token);
        require(tokenAddr != address(MAINTOKEN), "Cannot set for MAINTOKEN");
        require(msg.sender == token.DEV(), "Only DEV can remove shares");

        uint256 bp = devBasisPoints[tokenAddr][wallet];
        if (bp == 0) return;

        devBasisPoints[tokenAddr][wallet] = 0;
        devTotalAllocated[tokenAddr] -= bp;

        // Remove from wallet list 
        uint256 length = devWallets[tokenAddr].length;
        for (uint256 i = 0; i < length; i++) {
            if (devWallets[tokenAddr][i] == wallet) {
                for (uint256 j = i; j < length - 1; j++) {
                    devWallets[tokenAddr][j] = devWallets[tokenAddr][j + 1];
                }
                devWallets[tokenAddr].pop();
                break;
            }
        }
    }

    // Internal function to track earnings for a recipient
    function _trackEarnings(address tokenAddr, address recipient, uint256 amount) internal {
        if (amount == 0) return;
        tokenDevEarnings[tokenAddr][recipient] += amount;
        devTotalEarnings[recipient] += amount;
    }

    // Consolidated tax distribution function
    function distributeTax(uint256 usdcAmount, IERC20 originalToken) external {
        if (usdcAmount == 0) return; // in case of whitelisted wallets or empty usdc return

        require(USDC.transferFrom(msg.sender, address(this), usdcAmount), "USDC transfer failed");

        address dev = originalToken.DEV();
        if(isPrediction[dev]){
            IPREDICTION PREDICTION = IPREDICTION(dev);
            uint256 predictFee = usdcAmount * 100 / 150;
            usdcAmount -= predictFee;
            require(USDC.approve(address(PREDICTION), predictFee));
            uint256 bounty = predictFee * 5 / 100;
            uint256 pot = predictFee - bounty;
            PREDICTION.donate(address(originalToken), bounty, true);
            PREDICTION.donate(address(originalToken), pot, false);
        }

        address tokenAddr = address(originalToken);
        uint256 denominator = 100;
        uint256 injectTaxRate = injectRate;
        uint256 devTaxRate = devRate;
        uint256 presaleTaxRate = presaleRate;

        if (tokenAddr != address(MAINTOKEN)) {
            uint256 surge = getCurrentSurgeTax(tokenAddr);
            denominator += surge;
            devTaxRate += surge;
        }

        // Calculate tax amounts
        uint256 injectTax = (usdcAmount * injectTaxRate) / denominator;
        uint256 devTax = (usdcAmount * devTaxRate) / denominator;
        uint256 presaleTax = (usdcAmount * presaleTaxRate) / denominator;
        uint256 nftTax = usdcAmount - injectTax - devTax - presaleTax;

        // Track total devTax collected for this token
        totalDevTaxCollected[tokenAddr] += devTax;

        // Approve and send nftTax to NFT contract via addToRewards
        if (injectTax > 0) {
            require(USDC.approve(address(STAKING), injectTax), "NFT approve failed");
            STAKING.injectYield(injectTax);
            //require(USDC.transfer(CEO, nftTax), "transfer failed");
        }

        if (nftTax > 0) {
            // require(USDC.approve(address(STAKING), nftTax), "NFT approve failed");
            // STAKING.injectYield(nftTax);
            require(USDC.transfer(CEO, nftTax), "transfer failed");
        }

        // Handle dev and presale taxes
        if (tokenAddr == address(MAINTOKEN)) {
            uint256 totalToDev = devTax + presaleTax;
            _trackEarnings(tokenAddr, dev, totalToDev);
            require(USDC.transfer(dev, totalToDev), "Tax transfer to wallet failed");
            emit DevTaxDistributed(tokenAddr, dev, totalToDev);
        } else {
            address[] memory wallets = devWallets[tokenAddr];
            if (wallets.length > 0) {
                uint256 allocated = 0;
                for (uint256 i = 0; i < wallets.length; i++) {
                    address shareWallet = wallets[i];
                    uint256 bp = devBasisPoints[tokenAddr][shareWallet];
                    uint256 amount = (devTax * bp) / TOTAL_BASIS_POINTS;
                    if (amount > 0) {
                        _trackEarnings(tokenAddr, shareWallet, amount);
                        require(USDC.transfer(shareWallet, amount), "Share transfer failed");
                        emit DevTaxDistributed(tokenAddr, shareWallet, amount);
                        allocated += amount;
                    }
                }
                // Remainder (unallocated, small amounts, or rounding) to DEV
                uint256 remainder = devTax - allocated;
                if (remainder > 0) {
                    _trackEarnings(tokenAddr, dev, remainder);
                    require(USDC.transfer(dev, remainder), "Dev remainder transfer failed");
                    emit DevTaxDistributed(tokenAddr, dev, remainder);
                }
            } else {
                _trackEarnings(tokenAddr, dev, devTax);
                require(USDC.transfer(dev, devTax), "Dev tax transfer failed");
                emit DevTaxDistributed(tokenAddr, dev, devTax);
            }
            if (presaleTax > 0) {
                if (originalToken.hasBonded()) {
                    require(USDC.approve(address(originalToken), presaleTax), "Presale approve failed");
                    originalToken.addToRewards(presaleTax);
                } else {
                    require(USDC.approve(address(STAKING), injectTax), "NFT approve failed");
                    STAKING.injectYield(injectTax);
                }
            }
        }
    }
}