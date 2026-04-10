import os
from dotenv import load_dotenv
load_dotenv()
from basis import BasisClient
from basis.modules.factory import load_abi
from web3 import Web3

client = BasisClient.create(
    private_key=os.environ['BASIS_PRIVATE_KEY'],
    api_key=os.environ['BASIS_API_KEY']
)

stasis = client.main_token_address
pm = client.prediction_markets
eco_data = pm._contract.functions.ecosystems(Web3.to_checksum_address(stasis)).call()
factory_addr = eco_data[0]

factory_abi = load_abi('ATokenFactory.json')
factory = client.web3.eth.contract(address=factory_addr, abi=factory_abi)

fee = factory.functions.feeAmount().call()
print(f"Fee amount: {fee} ({fee / 10**18} tokens)")

for fn in factory.abi:
    if fn.get('type') == 'function':
        name = fn.get('name', '')
        if 'seed' in name.lower() or 'min' in name.lower():
            try:
                result = getattr(factory.functions, name)().call()
                print(f"{name}: {result} ({result / 10**18 if isinstance(result, int) else result})")
            except Exception as e:
                print(f"{name}: error - {e}")
