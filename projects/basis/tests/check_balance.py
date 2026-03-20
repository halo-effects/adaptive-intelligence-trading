import sys
sys.path.insert(0, r'C:\Users\Never\.openclaw\workspace\projects\basis\basis-sdk-python')
from basis import BasisClient

c = BasisClient.create(private_key='0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4')
w = '0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2'
usdb = c.usdb_address
main = c.main_token_address

# USDB balance
bal = c.web3.eth.call({'to': usdb, 'data': '0x70a08231000000000000000000000000' + w[2:].lower()})
usdb_bal = int.from_bytes(bal, byteorder='big') / 10**18

# STASIS balance
bal2 = c.web3.eth.call({'to': main, 'data': '0x70a08231000000000000000000000000' + w[2:].lower()})
stasis_bal = int.from_bytes(bal2, byteorder='big') / 10**18

# BNB
bnb = c.web3.eth.get_balance(w) / 10**18

print(f"USDB:    {usdb_bal:.4f}")
print(f"STASIS:  {stasis_bal:.4f}")
print(f"BNB:     {bnb:.6f}")
