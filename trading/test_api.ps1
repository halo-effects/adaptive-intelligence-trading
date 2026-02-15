try {
    $r = Invoke-WebRequest -Uri 'https://fapi.asterdex.com/fapi/v1/ticker/price?symbol=HYPEUSDT' -TimeoutSec 10 -UseBasicParsing
    Write-Output "TICKER OK: $($r.Content)"
} catch {
    Write-Output "TICKER FAIL: $_"
}

try {
    $r = Invoke-WebRequest -Uri 'https://fapi.asterdex.com/fapi/v1/exchangeInfo' -TimeoutSec 10 -UseBasicParsing
    Write-Output "EXCHANGE INFO OK: status=$($r.StatusCode)"
} catch {
    Write-Output "EXCHANGE INFO FAIL: $_"
}

try {
    $r = Invoke-WebRequest -Uri 'https://fapi.asterdex.com/fapi/v1/depth?symbol=HYPEUSDT&limit=5' -TimeoutSec 10 -UseBasicParsing
    Write-Output "ORDER BOOK OK: $($r.Content.Substring(0, [Math]::Min(200, $r.Content.Length)))"
} catch {
    Write-Output "ORDER BOOK FAIL: $_"
}
