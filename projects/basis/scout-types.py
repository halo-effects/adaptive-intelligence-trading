import sys; sys.path.insert(0, "sdk-python-v3")
from basis import BasisClient
client = BasisClient.create(private_key="062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4")

targets = {
    "LVTHN": "0xFf84209eBCCAc7328070E0011e973451c4a045F9",
    "MRINA": "0x3a0C6CE442Ad0F1E89cE38a7e773000903034A86",
    "TMPST": "0xC43DF80EFc3B29925BAbd744CD8AF28A0BE9AE3a",
    "BRINE": "0xB4916b462a69b9ce7be9e74138683D15208aB12f",
    "AGNT": "0x43e256d9A65bFcFCFe65154d9eDC058dcaE7B515",
    "PRINT": "0x0068bb0090906ce85e9510388696e8447455cf91",
    "CORAL": "0xB76951BC3A0Be01BCf0D4C7C696DC7a24b6a3F53",
    "TIDE": "0x36D6A57157fc8e28E1E2C2cC0c24AcF29de7DeCA",
    "KRAK": "0x113529d98Dac9b0b03B3B8D416A0D00e6F8b4d02",
    "NAUT": "0x4B5E9540A1d0EC3B9E5EE37ef3A45A2C10C76C6a",
}

for sym, addr in targets.items():
    try:
        info = client.api.get_token(addr)
        d = info.get("data", info)
        desc = d.get("description", "")[:80]
        mult = d.get("multiplier", "?")
        liq = d.get("liquidityUSD", "?")
        if isinstance(liq, float):
            liq = f"${liq:.2f}"
        print(f"{sym}: mult={mult} | liq={liq} | desc=\"{desc}\"")
    except Exception as e:
        print(f"{sym}: ERROR {e}")
