from dotenv import load_dotenv
from web3 import AsyncWeb3
import asyncio
from web3.providers.persistent import WebSocketProvider
from eth_abi.abi import decode
import os, json
from hexbytes import HexBytes

load_dotenv()
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
SWAP_ROUTER_ADDRESS = '0xE592427A0AEce92De3Edee1F18E0157C05861564'
SWAP_METHOD_SIGNATURE = 0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67

async def subscribe_to_uniswap_events():
    async with AsyncWeb3(WebSocketProvider(os.getenv("INFRA_WS"))) as w3:
        filter_params = {
            'topics':[
                w3.keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)"),
                HexBytes(HexBytes(SWAP_ROUTER_ADDRESS).rjust(32, b'\x00'))
            ]
        }

        subscription_id = await w3.eth.subscribe("logs", filter_params)
        print(f"Subscribing to swap events from swap router with id {subscription_id}")

        async for response in w3.socket.process_subscriptions():
            result = response['result']
            tx_hash = HexBytes(result['transactionHash']).hex()
            from_addr = decode(["address"], result["topics"][1])[0]
            to_addr = decode(["address"], result["topics"][2])[0]
            data = decode("int256,int256,uint160,uint128,int24".split(","), result["data"], strict=False)

            print(f"Transaction hash '0x{tx_hash}'")
            print(f"   Swapping from {from_addr} to {to_addr}")
            print(f"   Raw data: {data}\n")

async def subscribe_to_uniswap_events_via_contract():

    contract_instance = SWAP_ROUTER_ADDRESS
    abi = json.load(open('abi.json'))

    async with AsyncWeb3(WebSocketProvider(os.getenv("INFRA_WS"))) as w3:
        contract_instance = w3.eth.contract(address = SWAP_ROUTER_ADDRESS, abi=abi)
        while(True):
            latestBlock = await w3.eth.get_block('latest')

            print(f"|Looking at Block: {latestBlock['number']}|")
            # query each transaction hash
            for tx_hash in latestBlock["transactions"]:
                tx = await w3.eth.get_transaction(tx_hash)
                if tx['to'] == SWAP_ROUTER_ADDRESS:
                    res = contract_instance.decode_function_input(tx['input'])
                    print(res)


async def subscribe_to_transfer_events():
    async with AsyncWeb3(WebSocketProvider(os.getenv("INFRA_WS"))) as w3:
        transfer_event_topic = w3.keccak(text="Transfer(address,address,uint256)")
        filter_params = {
            "address": WETH_ADDRESS,
            "topics": [transfer_event_topic],
        }
        subscription_id = await w3.eth.subscribe("logs", filter_params)
        print(f"Subscribing to transfer events for WETH at {subscription_id}")

        async for payload in w3.socket.process_subscriptions():
            result = payload["result"]

            from_addr = decode(["address"], result["topics"][1])[0]
            to_addr = decode(["address"], result["topics"][2])[0]
            amount = decode(["uint256"], result["data"])[0]
            print(f"{w3.from_wei(amount, 'ether')} WETH from {from_addr} to {to_addr}")


asyncio.run(subscribe_to_uniswap_events())