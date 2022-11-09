# Decode read-back bytes array into file
def decode(returned_bytes):
    bits_amount = len(returned_bytes) * 8
    high = 0
    i = 1
    for byte in returned_bytes:
        high = high | ( byte << bits_amount -8*i)
        i+=1
    
    return high

class Decode:

    def __init__(self):
        self.full_msg = ''

    def add(self, msg):
        self.full_msg += "{0:b}\n".format(decode(msg))

    def save(self):
        with open('D:/My_projects/python_projects/engine/src/decode.txt', 'w') as file:  
            try: file.truncate(0)
            except Exception as file_error:
                print(file_error)

            file.write(self.full_msg)

