import datetime
import os
import shutil
import sys
import json
import struct
from time import sleep

def getMessage():
    rawLength = sys.stdin.buffer.read(4)
    if len(rawLength) == 0:
        sys.exit(0)
    messageLength = struct.unpack('@I', rawLength)[0]
    message = sys.stdin.buffer.read(messageLength).decode('utf-8')
    return json.loads(message)

# Encode a message for transmission,
# given its content.
def encodeMessage(messageContent):
    encodedContent = json.dumps(messageContent).encode('utf-8')
    encodedLength = struct.pack('@I', len(encodedContent))
    return {'length': encodedLength, 'content': encodedContent}

# Send an encoded message to stdout
def sendMessage(encodedMessage):
    sys.stdout.buffer.write(encodedMessage['length'])
    sys.stdout.buffer.write(encodedMessage['content'])
    sys.stdout.buffer.flush()



import maya
from twisted.logger import globalLogPublisher

from umbral.keys import UmbralPublicKey
from nucypher.characters.lawful import Alice, Bob, Ursula
from nucypher.characters.lawful import Enrico as Enrico
from nucypher.crypto.powers import SigningPower
from nucypher.network.middleware import RestMiddleware
from nucypher.utilities.logging import SimpleObserver



######################
# Boring setup stuff #
######################
sendMessage(encodeMessage("Connecting to NuCypher network...")) 
# Execute the download script (download_finnegans_wake.sh) to retrieve the book
BOOK_PATH = os.path.join('.', 'finnegans-wake.txt')

# Change this value to to perform more or less total re-encryptions
# in order to avoid processing the entire book's text. (it's long)
NUMBER_OF_LINES_TO_REENCRYPT = 25

# Twisted Logger
globalLogPublisher.addObserver(SimpleObserver())


#######################################
# Finnegan's Wake on NuCypher Testnet #
# (will fail with bad connection) #####
#######################################

SEEDNODE_URI = "https://localhost:11501"

##############################################
# Ursula, the Untrusted Re-Encryption Proxy  #
##############################################
ursula = Ursula.from_seed_and_stake_info(seed_uri=SEEDNODE_URI,
                                         federated_only=True,
                                         minimum_stake=0)

# Here are our Policy details.
policy_end_datetime = maya.now() + datetime.timedelta(days=5)
m, n = 2, 3
label = b"secret/files/and/stuff"
sendMessage(encodeMessage("Label: {}".format(label.decode('ascii'))))
sendMessage(encodeMessage("policy_end_datetime: {}".format(policy_end_datetime)))
######################################
# Alice, the Authority of the Policy #
######################################

ALICE = Alice(network_middleware=RestMiddleware(),
              known_nodes=[ursula],
              learn_on_same_thread=True,
              federated_only=True)

# Alice can get the public key even before creating the policy.
# From this moment on, any Data Source that knows the public key
# can encrypt data originally intended for Alice, but that can be shared with
# any Bob that Alice grants access.
policy_pubkey = ALICE.get_policy_pubkey_from_label(label)

BOB = Bob(known_nodes=[ursula],
          network_middleware=RestMiddleware(),
          federated_only=True,
          start_learning_now=True,
          learn_on_same_thread=True)

ALICE.start_learning_loop(now=True)

policy = ALICE.grant(BOB,
                     label,
                     m=m, n=n,
                     expiration=policy_end_datetime)

assert policy.public_key == policy_pubkey

# Alice puts her public key somewhere for Bob to find later...
alices_pubkey_bytes_saved_for_posterity = bytes(ALICE.stamp)

# ...and then disappears from the internet.
del ALICE

#####################
# some time passes. #
# ...               #
#                   #
# ...               #
# And now for Bob.  #
#####################

#####################
# Bob the BUIDLer  ##
#####################

BOB.join_policy(label, alices_pubkey_bytes_saved_for_posterity)

# Now that Bob has joined the Policy, let's show how Enrico the Encryptor
# can share data with the members of this Policy and then how Bob retrieves it.
# In order to avoid re-encrypting the entire book in this demo, we only read some lines.
with open(BOOK_PATH, 'rb') as file:
    finnegans_wake = file.readlines()[:NUMBER_OF_LINES_TO_REENCRYPT]

print()
print("**************James Joyce's Finnegan's Wake**************")
print()
print("---------------------------------------------------------")
sendMessage(encodeMessage("Getting access to James Joyce's Finnegan's Wake")) 
for counter, plaintext in enumerate(finnegans_wake):

    #########################
    # Enrico, the Encryptor #
    #########################
    enrico = Enrico(policy_encrypting_key=policy_pubkey)

    # In this case, the plaintext is a
    # single passage from James Joyce's Finnegan's Wake.
    # The matter of whether encryption makes the passage more or less readable
    # is left to the reader to determine.
    single_passage_ciphertext, _signature = enrico.encrypt_message(plaintext)
    data_source_public_key = bytes(enrico.stamp)
    del enrico

    ###############
    # Back to Bob #
    ###############

    enrico_as_understood_by_bob = Enrico.from_public_keys(
        {SigningPower: data_source_public_key},
        policy_encrypting_key=policy_pubkey
    )

    # Now Bob can retrieve the original message.
    alice_pubkey_restored_from_ancient_scroll = UmbralPublicKey.from_bytes(alices_pubkey_bytes_saved_for_posterity)
    delivered_cleartexts = BOB.retrieve(message_kit=single_passage_ciphertext,
                                        data_source=enrico_as_understood_by_bob,
                                        alice_verifying_key=alice_pubkey_restored_from_ancient_scroll,
                                        label=label)

    # We show that indeed this is the passage originally encrypted by Enrico.
    assert plaintext == delivered_cleartexts[0]
    sendMessage(encodeMessage(format(delivered_cleartexts[0])))
    #print("Retrieved: {}".format(delivered_cleartexts[0]))

