import canopen
import usb
import can
import canalystii
from bitarray import bitarray 
import usb.backend.libusb1
from . import crc_creators




# bitflow creating for crc calculation
def get_bitflow(msg)->int:
    free_space = (8 * msg.dlc) + 19         # get bit size of data section
    bitflow = bitarray(free_space)      
    bitflow.setall(1)

    bitflow = int(bitflow.to01(), base=2)   # empty bitflow

    shift = msg.id << free_space - 12
    bitflow = bitflow & shift
    free_space-=12 


    shift = msg.control << free_space - 3
    bitflow = bitflow | shift
    free_space-=3 


    shift = msg.dlc << free_space - 4
    bitflow = bitflow | shift
    free_space-=4 


    for databyte in msg.data:
        shift = databyte << free_space - 8
        bitflow = bitflow | shift
        free_space-=8
    
    return bitflow

bits_amount = lambda x: len(bin(x)) - 2     # helpful expression

# creating byte arrays for crc calculation
def get_reverse_bytes(bitflow)->list:

    full_octets = bits_amount(bitflow) // 8
    bits_remainder = bits_amount(bitflow) - full_octets*8
    bytelist = []
    byteamount = 1
    str_bitflow = "{0:b}".format(bitflow)

    bytelist.append(str_bitflow[:bits_remainder])
    
   
    for index in range(full_octets,0,-1):
        bytelist.append(str_bitflow[
            len(str_bitflow) - 8*index : len(str_bitflow) - (8*(index-1))
            ])
    
    result = []
    for el in bytelist:
        result.append(int(el,base=2))

    return result

def get_bytes(bitflow,padding='0')->list:
    """padding = 0: fills in the missing bits with 0 (001 -> 001+0 0000)
    padding = 1: fills in the missing bits with 1 (001 -> 001+1 1111)
    padding = rev: fills in the missing bits with 0 in high rank (001 -> 0000 0+001)"""
    full_octets = (bits_amount(bitflow)+1) // 8
    bits_remainder = (bits_amount(bitflow)+1) - full_octets*8
    s = "{0:b}".format(bitflow)
    byte_array = []

    byte_array.append(s[0:7])

    for i in range(1, full_octets):
        i*=8

        byte_array.append(s[i-1:(i-1)+8])

    if bits_remainder != 0:
        if padding == 'rev':
            byte_array.append(s[len(s)-bits_remainder:])
        else:    
            s = s[len(s)-bits_remainder:]
            for i in range(0, 8-bits_remainder):
                s+=padding

            byte_array.append(s)



    result = []
    for el in byte_array:
        result.append(int(el,base=2))

    return result




#reversing crc [high <-> low] 
def reverse(val)->int:
    high = hex(val)[2:4]
    low = hex(val)[4::]
    return int((low + high),base=16)

# filling bitflow with stuff bits [sof...ack]
def create_excess(bitflow)->int:
    counter_1 = 0
    counter_0 = 0
    str_bitflow = "{0:b}".format(bitflow)[:(bits_amount(bitflow)-1)]
    excess_amount = 0       

    for index,bit in enumerate("{0:b}".format(bitflow)):   
        if bit == '1':
            counter_0 = 0
            counter_1+=1

            if counter_1 == 6: 
                   
                str_bitflow = str_bitflow[:(index+excess_amount)] + '0' + str_bitflow[(index+excess_amount):]
                excess_amount+=1
                counter_1 =1

        else:
            counter_1 = 0
            counter_0+=1

            if counter_0 == 6:
                
                str_bitflow = str_bitflow[:(index+excess_amount)] + '1' + str_bitflow[(index+excess_amount):]
                excess_amount+=1
                counter_0 =1

    return int(str_bitflow,base=2)

#adding crc to bitflow
def add_to_bitflow(crc, bitflow):
    joint_bitflow = (bitflow << 16) | crc
    return joint_bitflow

#showing bitflow in bin and bytes
def show_bitflow(bitflow):
    print("bitflow_bin:   ", "{0:b}".format(bitflow))
    print("bitflow_bytes: ", end=' ') 
    for byte in get_bytes(bitflow):
        print(hex(byte), end=' ')           
    print("")

def create_crc(msg):                        
             
    bitflow = get_bitflow(msg)              #creating a bit sequence for a crc calculation [sof,id,control,dlc,data]. 
                                           
    print("BITFLOW FOR A CRC CALCULATION")
    show_bitflow(bitflow)

    #print("REVERSE BITFLOW FOR A CRC CALCULATION")
    #print(get_reverse_bytes(bitflow))
    

    #----------- creating 15-bit crc ----------- 

    #polinom from CAN description:  0x4599 0xC599 0x4CD1 0x62CC
    #crc = crc_creators.crc_remainder("{0:b}".format(bitflow), "{0:b}".format(0x4599), '0')   #creating crc-15 using str-polinom
    #crc = int(crc, base=2)

    #crc = crc_creators.crc_15_can(bitflow=bitflow, divizor=0x62CC)     #creating crc-15 using polinom (divizor). User-defined function


    #----------- creating 16-bit crc -----------

    #for creating crc-16 you need to use byte arrays. Reverse or simple:
    byte_array = get_reverse_bytes(bitflow)                                             
    #byte_array = get_bytes(bitflow,padding='0')

    #crc = crc_creators.modbus_16_2(byte_array)                         #creating crc-16 from modbus_16. Need to reverse high and low bytes 
    #crc = crc_creators.modbus_16(byte_array)                           #creating crc-16 from modbus_16. Need to reverse high and low bytes 
    #crc = crc_creators.arc_16_table(byte_array)                        #creating reverse crc-16 from modbus_16 using table. Ready to send into bus        
    #crc = crc_creators.arc_16_poli(byte_array)                         #creating reverse crc-16 from modbus_16 using polinom. Ready to send into bus   

    #crc = crc_creators.ccitt_16_table(byte_array)                      #creating crc ccitt_16 using table                                 
    crc = crc_creators.ccitt_16_poli(byte_array)                       #creating crc ccitt_16 using polinom                             

    #crc = crc_creators.crc_16_alter(byte_array)                        #creating crc-16 using polinom. 


    #----------- creating reverse crc ----------- 

    crc_rev = reverse(crc)                  
    print("modbus CRC reverse: ", hex(crc_rev))


    print("CRC:    {0}          hex: {1}".format(bin(crc), hex(crc)))
    print("crc bits amount: ", bits_amount(crc))

    #crc = (crc << 1) | 1                                                #add delimiter = '1' to 15-bit crc
    joint_bitflow = add_to_bitflow(crc, bitflow)                        #add crc section to bitflow

    return (crc,joint_bitflow)


class SDO:
    sof     = 0x00      # start of frame
    id      = 0x600     # id SDO package 0x600
    control = 0x00      # control = [rtr | r1 | r0] = [0 | 0 | 0] defoult
                        #rtr =  0 default (dominant for data frame. only data frames)       
                        #r1  =  0 default (dominant for standart identifier. Only. standart identifiers)
                        #r0  =  0 defoult ---reserved bits must be dominant
    ack     = 0x03      # ack = [ack | delim] = [1 | 1] defoult. 
                        # ack = 1 defoult. Transmitter sends rececive, reciever asserts dominant     MAY BE equal "0" 
                        # delim = 1 defoult. Rececive defoult
    eof     = 0x7F      # 7 bit rececive defoult. end of package. 

    def __init__(self, node_id, data):
        self.id = self.id | node_id                     # id sdo package 0x600 + node id 
        self.dlc = len(data)                            # dlc = data section length
        self.data = data
        (self.crc,self.bitflow) = create_crc(self)      # creating crc section and bitflow
        

    def show(self):
        print("sof:     ", self.sof)
        print("ID:      ", self.id)
        print("control: ", self.control)
        print("- rtr:     ", (self.control & 0x04)>>2)
        print("- r1:      ", (self.control & 0x02)>>1)
        print("- r0:      ", (self.control & 0x01))
        print("DLC:     ", self.dlc)
        print("DATA:    ", self.data)
        print("CRC:     ", self.crc)
        print("ack:     ", self.ack)
        print("- ack:     ", (self.ack & 0x02)>>1)
        print("- delim:   ", (self.ack & 0x01))
        print("eof:     ", self.eof)
        print("bitflow: ")
        show_bitflow(self.bitflow)

    def build_can_dataframe(self):
        
        extend_bitflow = create_excess(self.bitflow)                       #each 5+ same value bits sequence is divided with an opposite value bit. From sof to crc section including.
        extend_bitflow = end_of_pkg(extend_bitflow, self.ack, self.eof)    #adding the ack and eof bits into bitflow
        
        print("FULL BITFLOW WITH STUFF BITS: ")
        show_bitflow(extend_bitflow)

        return get_bytes(extend_bitflow,padding='1')                       #creating can_dataframe with padding the last byte with '1' sequence

# add ack and eof bits into bitflow
def end_of_pkg(bitflow,ack,eof):
    return (bitflow << 9) | (ack << 7) | eof

# show the dataframe
def show_frame(can_dataframe):
    print("DATAFRAME: ", end=' ')
    for byte in can_dataframe:
        print(hex(byte), end=' ')
    
    print("")







def test():
    
    polinom = "{0:b}".format(0xB1)
    crc = crc_creators.crc_remainder('1011101101111010100101101000', polinom, '0')
    print("CRC: ",hex(int(crc,base=2)))

def test_2():
    #bitflow = 0x34EC    11010011101100
    #divizor = 0xB       1011
    crc_creators.crc_calc(bitflow=0x34EC, divizor=0xB)

def test_x():
    
    expect_result2 = '110011101001100'   #15-bit crc                 polinom: 0x86EE
    crc = ''
    i = 0
    polinom = "{0:b}".format(i)
    while crc != expect_result2:
        i+=1
        print("i:", i)
        polinom = "{0:b}".format(i)
        crc = crc_creators.crc_remainder('0101010101010000000', polinom, '0')
        print("crc: ",crc)

    
        
    res = crc_creators.crc_check('0101010101010000000', polinom, crc)
    print(res)
    print("polinom: ", polinom)






if __name__ == "__main__":


    initialization_start = (0x01, 0x00)	#01 h Start network node
    initialization_oper =  (0x80, 0x00)	#02 h Stop network node
                                        #80 h Go to “Pre-operational”
                                        #81 h Reset node
                                        #82 h Reset communication

    control_word_0F = (0x2B, 0x40, 0x60, 0x00, 0x0F, 0x00)
    work_mode =     (0x2F, 0x60, 0x60, 0x00, 0x01)                         # work mode 1       
    actual_position = (0x40, 0x64, 0x60, 0x00)
    speed = (0x23, 0x81, 0x60, 0x00, 0xE8, 0x03, 0x00, 0x00)
    acceleration = (0x23, 0x83, 0x60, 0x00, 0x20, 0x4E, 0x00, 0x00)
    control_word_2F =  (0x2B, 0x40, 0x60, 0x00, 0x2F, 0x00)                # control word 2F      
    location_cash = (0x23, 0x7A, 0x60, 0x00, 0xE0, 0x93, 0x04, 0x00)       # location cash 300 000 = 04 93 E0
    status = (0x40, 0x41, 0x60, 00)

    dataframe = [initialization_start, initialization_oper, control_word_0F, work_mode, actual_position, speed, acceleration, control_word_2F, location_cash, status]

    for data in dataframe:

        package = SDO(1,data=data)
        can_dataframe = package.build_can_dataframe()
        show_frame(can_dataframe)
        print("")
    
    #test_2()
    

