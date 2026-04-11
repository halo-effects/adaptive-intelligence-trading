# -*- coding: utf-8 -*-
"""Add images to CSTACK and AISTACK tokens."""
import sys, io
sys.stdout.reconfigure(encoding='utf-8')
from basis import BasisClient
from PIL import Image

PK = "062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4"
CONTRACTS = {
    "factory_address": "0xB6BA282f29A7C67059f4E9D0898eE58f5C79960D",
    "swap_address": "0x9F9cF98F68bDbCbC5cf4c6402D53cEE1D180715f",
    "market_trading_address": "0x396216fc9d2c220afD227B59097cf97B7dEaCb57",
    "loan_hub_address": "0xFe19644d52fD0014EBa40c6A8F4Bfee4Ce3B2449",
    "staking_address": "0x1FE7189270fb93c32a1fEfA71d1795c05C41cb33",
    "reader_address": "0xF406cA6403c57Ad04c8E13F4ae87b3732daa087d",
    "usdb_address": "0x42bcF288e51345c6070F37f30332ee5090fC36BF",
    "main_token_address": "0x3067ce754a36d0a2A1b215C4C00315d9Da49EF15",
    "resolver_address": "0xB5FFCCB422531Cf462ec430170f85d8dD3dC3f57",
    "leverage_address": "0xeffb140d821c5B20EFc66346Cf414EeAC8A8FDB2",
    "taxes_address": "0x4501d1279273c44dA483842ED17b5451e7d3A601",
    "vesting_address": "0xedd987c7723B9634b0Aa6161258FED3e89F9094C",
    "private_market_address": "0x28675A82ee3c2e6d2C85887Ea587FbDD3E3C86EE",
}

c = BasisClient.create(private_key=PK, **CONTRACTS)
print("Authenticated.")

CSTACK = "0xADeCa6980c92466947704875c7D1e6aa9081cCB7"
AISTACK = "0xEC0c36e37F7C7b817650cA68e64dF5a7e8c4dbfD"
IMG_PATH = r"C:\Users\Never\.openclaw\media\inbound\file_582---f12dbc83-99cb-4971-89f0-7ed55653b7aa.jpg"

# Convert to WebP 512x512
img = Image.open(IMG_PATH)
w, h = img.size
side = min(w, h)
left = (w - side) // 2
top = (h - side) // 2
img = img.crop((left, top, left + side, top + side))
img = img.resize((512, 512), Image.LANCZOS)
buf = io.BytesIO()
img.save(buf, format="WEBP", quality=90)
print(f"Image: {buf.getbuffer().nbytes} bytes WebP 512x512")

# Upload with purpose=token
buf.seek(0)
files = {"file": ("cstack.webp", buf, "image/webp")}
data = {"purpose": "token", "address": CSTACK}
url = "https://launchonbasis.com/api/images"
resp = c.api.session.post(url, files=files, data=data)
print(f"Upload status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")

if resp.status_code == 200:
    # Parse image URL
    try:
        img_url = resp.json()
        if isinstance(img_url, dict):
            img_url = img_url.get("url", img_url.get("image", str(img_url)))
    except:
        img_url = resp.text.strip().strip('"')
    
    print(f"Image URL: {img_url}")
    
    # Update CSTACK
    meta = c.api.update_metadata(address=CSTACK, image=img_url)
    print(f"CSTACK metadata: {meta}")
    
    # Update AISTACK
    meta2 = c.api.update_metadata(address=AISTACK, image=img_url)
    print(f"AISTACK metadata: {meta2}")
    
    print("\nDone! Both tokens should now have images.")
else:
    print(f"Upload failed: {resp.text}")
