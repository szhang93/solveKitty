import requests
import json
from web3 import Web3
import abi
from datetime import datetime
from web3.logs import STRICT, IGNORE, DISCARD, WARN
from attributedict.collections import AttributeDict
from hexbytes import HexBytes

# Infura URL
url = 'https://mainnet.infura.io/v3/78069d72b81f4ecfb015f49e0801102f'
contractAddress = '0x06012c8cf97BEaD5deAe237070F9587f8E7A266d'
web3 = Web3(Web3.HTTPProvider(url))
contract = web3.eth.contract(address=contractAddress, abi=abi.ABI)
# Hashed value of the Birth() event
birthEvent = Web3.toHex(Web3.keccak(text='Birth(address,uint256,uint256,uint256,uint256)'))


"""
Queries using Infura to retrieve logs.
The payload uses the Birth() event as a filter because we only care about those.
Returns data in json format.
"""
def getLogs(fromBlock, toBlock):
    print('Querying blocks from ', fromBlock, 'to ', toBlock)
    headers = {'content-type': 'application/json'}
    payload = {
        'jsonrpc':'2.0',
        'method':'eth_getLogs',
        'params': [
            {'address': contractAddress,
            'fromBlock': Web3.toHex(fromBlock),
            'toBlock': Web3.toHex(toBlock),
            'topics': [birthEvent]}
            ],
        'id':1
    }
    # Makes post requests
    r = requests.post(url, data = json.dumps(payload))
    # Converts byte list to json
    decodedContent = r.content.decode("utf-8")
    data = json.loads(decodedContent)
    return data

"""
This function is necessary as the log needs to be formatted in the way
'contract.events.Birth().processLog(log)' processes it. Namely,
the log must be converted from a Dictionary to an Attribute Dictionary.

Also, the hex numbers need to be converted from string to hexbytes for:
blockHash, topics, transactionHash
blockNumber, logIndex, and transactionIndex must be converted from
hex string to integer
"""
def convertLog(log):
    log = AttributeDict(log)
    log.blockHash = HexBytes(int(log.blockHash, 16))
    log.transactionHash = HexBytes(int(log.transactionHash, 16))
    encodedTopics = []
    for topic in log.topics:
        encodedTopics.append(HexBytes(int(topic, 16)))

    log.topics = encodedTopics
    log.blockNumber = int(log.blockNumber,16)
    log.logIndex = int(log.logIndex,16)
    log.transactionIndex = int(log.transactionIndex,16)
    return log
    # print(log)





"""
Returns total births and the kitty with the most births from the starting block
to ending block.
Because Infura getLogs only allows for 10000 logs at a time, we have to call
getLogs multiple times in intervals. Since the the runtime of this program is
a bit long, the interval will be set to 100 just so I can see the updates.

Uses a Dictionary to keep track of the number of births of each matron, where
the key is the matron's ID.
Additionally, uses a Set to keep track of the birth of each kitty. For some reason,
I'm encountering duplicate logs
"""
def solveKitty(start, fin):
    INTERVAL = 5000
    totalBirths = mostBirths = 0
    kittyWithMostBirths = None # stores ID of kitty with most births
    matrons = {} # Dictionary of natrons and the corresponding number of births
    newBorns = set() # Set of each new kitty that was born

    end = min(fin, start + INTERVAL) # Ending block of the current block interval
    while(start <= end):
        data = getLogs(start, end) # Retrieve logs from this interval

        for log in data['result']:
            # Decode the log to obtain the kittyId passed into the Birth event
            tx = log['transactionHash']
            """
            TOO SLOW
            receipt = web3.eth.getTransactionReceipt(tx)
            logs = contract.events.Birth().processReceipt(receipt)
            """

            log = convertLog(log)
            # processed_log = contract.events.Birth().processLog(receipt['logs'][0])
            logs = contract.events.Birth().processLog(log)

            # If the newBorn is a duplicate, ignore it
            newBornId = logs['args']['kittyId']
            if newBornId in newBorns:
                continue

            newBorns.add(newBornId)
            matronId = logs['args']['matronId']
            totalBirths += 1
            # print('Processing kittyId ', kittyId)
            # Store kittyID into dictionary
            if matronId in matrons:
                matrons[matronId] += 1
            else:
                matrons[matronId] = 1
            # If matronId == 0, the cat is 1st generation so it doesn't count
            if matrons[matronId] > mostBirths and matronId != 0:
                mostBirths = matrons[matronId]
                kittyWithMostBirths = matronId

        print('total births so far: ', totalBirths)
        print('most births so far: ', mostBirths, ' by ', kittyWithMostBirths)

        start = start + INTERVAL + 1
        end = min(fin, start + INTERVAL)

    # print(matrons)
    # print(newBorns)
    return (totalBirths, mostBirths, kittyWithMostBirths)

"""
Calls contract method getKitty to get kitty's data
"""
def getKittyData(kittyId):
    kittyData = contract.functions.getKitty(kittyId).call()
    """
    GetKitty returns:
        bool isGestating,
        bool isReady,
        uint256 cooldownIndex,
        uint256 nextActionAt,
        uint256 siringWithId,
        uint256 birthTime,
        uint256 matronId,
        uint256 sireId,
        uint256 generation,
        uint256 genes
    """
    if kittyData == None:
        return None
    return (kittyData[5], kittyData[8], kittyData[9])


if __name__ == '__main__':
    # startingBlock=6607985 and endingBlock=7028323
    totalBirths, mostBirths, kittyWithMostBirths = solveKitty(6607985, 6608185)
    print('FINAL ANSWER -------------------------')
    print('total births: ', totalBirths)
    print('most births: ', mostBirths)
    print('kitty with most births: ', kittyWithMostBirths)
    birthTime, generation, genes = getKittyData(kittyWithMostBirths)
    birthTime = datetime.fromtimestamp(birthTime)
    print('birthTime=', birthTime,' generation=', generation, ' genes=', genes)
