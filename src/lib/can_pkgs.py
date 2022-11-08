import canopen
import usb
import can
import canalystii
from bitarray import bitarray 
import usb.backend.libusb1
import sys
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

def get_bytes(bitflow,param='0')->list:
    """param = 0: fills in the missing bits with 0 (001 -> 001+0 0000)
    param = 1: fills in the missing bits with 1 (001 -> 001+1 1111)
    param = rev: fills in the missing bits with 0 in high rank (001 -> 0000 0+001)"""
    full_octets = (bits_amount(bitflow)+1) // 8
    bits_remainder = (bits_amount(bitflow)+1) - full_octets*8
    s = "{0:b}".format(bitflow)
    byte_array = []
    #print("append ", s[0:7])
    byte_array.append(s[0:7])

    for i in range(1, full_octets):
        i*=8
        #print("append ", s[i-1:(i-1)+8])
        byte_array.append(s[i-1:(i-1)+8])

    if bits_remainder != 0:
        if param == 'rev':
            byte_array.append(s[len(s)-bits_remainder:])
        else:    
            s = s[len(s)-bits_remainder:]
            for i in range(0, 8-bits_remainder):
                s+=param
            #print("s",s)
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
    str_bitflow = "{0:b}".format(bitflow)
    excess_amount = 0       

    for index,bit in enumerate("{0:b}".format(bitflow)):   
        if bit == '1':
            counter_0 = 0
            counter_1+=1
            #print("bit == 1.    counter_0: {0}      counter_1: {1}".format(counter_0, counter_1))  
            if counter_1 == 6: 
                   
                str_bitflow = str_bitflow[:(index+excess_amount)] + '0' + str_bitflow[(index+excess_amount):]
                excess_amount+=1
                counter_1 =1
                #print("counter_1", str_bitflow)
        else:
            counter_1 = 0
            counter_0+=1
            #print("bit == 0.    counter_0: {0}      counter_1: {1}".format(counter_0, counter_1))  
            if counter_0 == 6:
                
                str_bitflow = str_bitflow[:(index+excess_amount)] + '1' + str_bitflow[(index+excess_amount):]
                excess_amount+=1
                counter_0 =1
                #print("counter_0                   ", str_bitflow)

    #print("joint_bitflow after excess  ", str_bitflow)
    return int(str_bitflow,base=2)

#adding crc to bitflow
def add_to_bitflow(crc, bitflow):
    joint_bitflow = (bitflow << 16) | crc
    #print("joint_bitflow before excess ", "{0:b}".format(joint_bitflow))
    return joint_bitflow

#showing bitflow in bin and bytes
def show_bitflow(bitflow):
    print("bitflow_bin:   ", "{0:b}".format(bitflow))
    print("bitflow_bytes: ", end=' ') 
    for byte in get_bytes(bitflow):
        print(hex(byte), end=' ')           
    print("")

def create_crc(msg):                        
             
    bitflow = get_bitflow(msg)              # creating a bit sequence for a crc calculation [sof,id,control,dlc,data]. 
                                           
    print("BITFLOW FOR A CRC CALCULATION")
    show_bitflow(bitflow)

    print("REVERSE BITFLOW FOR A CRC CALCULATION")
    print(get_reverse_bytes(bitflow))
    
    #----------- creating crc ----------- 

    #get_reverse_bytes(bitflow)         - arguments for crc creating functions
    #get_bytes(bitflow,param='0')

    #polinom from modbus description: 8005 / A002
    #crc_16bit = crc_creators.crc_remainder("{0:b}".format(bitflow), "{0:b}".format(0x8005), '0')
    #crc_16bit = int(crc_16bit, base=2)

    #polinom for 15-bit crc (need crc_delim=1): 0xA5E6  
    #crc_15bit = crc_creators.crc_remainder("{0:b}".format(bitflow), "{0:b}".format(0xA5E6), '0')
    #crc_15bit = int(crc_15bit, base=2) 
    #crc_15bit = (crc_15bit << 1) | 1               # delim 




    #crc_16bit = crc_creators.modbus_16(get_bytes(bitflow))                 #creating crc from modbus_16. Need to reverse high and low bytes 
    #crc_16bit = crc_creators.modbus_16_2(get_reverse_bytes(bitflow))       #creating crc from modbus_16. Need to reverse high and low bytes 
    #crc_16bit = crc_creators.arc_16(get_reverse_bytes(bitflow))            #creating reverse crc from modbus_16 using table. Ready to send into bus        
    crc_16bit = crc_creators.modbus_16_3(get_reverse_bytes(bitflow))        #creating reverse crc from modbus_16 using polinom. Ready to send into bus   

    
    #crc_16bit = crc_creators.ccitt_table_16(get_reverse_bytes(bitflow))     #creating crc ccitt_16 with table                                 
    #crc_16bit = crc_creators.ccitt_16(get_bytes(bitflow,param='0'))         #creating crc ccitt_16 using polinom                             
                      
    #crc_16bit = crc_creators.can_crc_next(get_bytes(bitflow,param='0'))     # crc-16 using polinom


    #print("CRC:    {0}          hex: {1}".format(bin(crc_16bit), hex(crc_16bit)))

    #----------- creating reverse crc ----------- 
    crc_16bit_rev = reverse(crc_16bit)                  
    print("modbus CRC reverse: ", hex(crc_16bit_rev))



    joint_bitflow = add_to_bitflow(crc_16bit, bitflow)              # add crc section to bitflow



    return (crc_16bit,joint_bitflow)


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
        self.id = self.id | node_id         # id sdo package 0x600 + node id 
        self.dlc = len(data)                # dlc = data section length
        self.data = data
        (self.crc,self.bitflow) = create_crc(self)     # creating crc section and bitflow
        

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
        
        print("EXTEND BITFLOW: ")
        show_bitflow(extend_bitflow)

        return get_bytes(extend_bitflow,param='1')                                  #creating can_dataframe
                                                                          #need to specify param='1' ?
        #array = []
        #array.append(first_byte(self.id))
        #array.append(second_byte(self.id, self.control, self.dlc))
        #array.append(third_byte(self.dlc, self.data))

        #for i in range(1, self.dlc):
        #    array.append(data_section(self.data, i))
        
        #array.append(crc_section_high(self.data, self.crc))
        #array.append(crc_section_low(self.crc))

        #array.append(end_of_pkg_byte(self.crc, self.ack, self.eof))

        #array.append(eof_itm())

        #return array


def end_of_pkg(bitflow,ack,eof):
    return (bitflow << 9) | (ack << 7) | eof


# creating first byte
def first_byte(id)->int:
    bufer = id & 0x7F0
    #print("bufer: ", bin(bufer))
    result = bufer >> 4
    #print("result: ", bin(result))
    return result

# creating second byte
def second_byte(id, control, dlc)->int:
    bufer = id & 0x0F
    bufer_shift = bufer << 4

    control_shift = control << 1

    bufer = (dlc & 0x08) >> 3

    result = bufer_shift | control_shift | bufer
    return result

# creating third byte 
def third_byte(dlc, data):
    bufer = dlc & 0x07
    dlc_shift = bufer << 5

    bufer = data[0] & 0xF8    #first 5 bits from the first byte of data
    second_part = bufer >> 3

    result = dlc_shift | second_part
    return result

# creating data bytes
def data_section(data, i):
    prev = data[i-1]
    current = data[i]

    bufer = prev & 0x07
    high_shift = bufer << 5

    bufer = current & 0xF8
    low_shift = bufer >> 3

    result = high_shift | low_shift
    return result

# creating crc first byte
def crc_section_high(data, crc):

    extention = 16 - bits_amount(crc)
    bufer = data[len(data) - 1] & 0x07
    high_shift = bufer << 5

    if bits_amount(crc) <= 11:
        return high_shift
    elif extention == 0: 
        bufer = crc & 0xF800
        low_shift = bufer >> 11

        result = high_shift | low_shift
        return result
    else:                                              # extended crc_section_high byte with "zeros" if checksum+delim size is consist of less than 16 bits 
        mask_bits_amount = bitarray(5 - extention)     # amount of bits=1 for mask  
        mask_bits_amount.setall(1)

        mask = int(mask_bits_amount.to01(), base=2)
        
        bufer = mask << bits_amount(crc) - bits_amount(mask)
        #print("mask after shift (bufer): ", bin(bufer))

        bufer = crc & bufer
        #print("bufer", bin(bufer))

        low_shift = bufer >> bits_amount(crc) - bits_amount(mask)
        #print("low_shift", bin(low_shift))

        result = high_shift | low_shift
        #print("result", bin(result))

        return result
        
# creating crc second byte
def crc_section_low(crc):
    if bits_amount(crc) <= 3:
        return 0x00
    else: 
        bufer = crc & 0x7F8
        result = bufer >> 3

        return result
    


# creating ack and eof bytes
def end_of_pkg_byte(crc, ack, eof):
    bufer = crc & 0x07
    shift_high = bufer << 5

    ack_shift = ack << 3

    bufer = eof & 0x70
    eof_shift = bufer >> 4

    result = shift_high | ack_shift | eof_shift
    return result

# creating padding (eof + padding)
def eof_itm():
    #result = 0xFE

    #result = 0xFF
    result = 0xF0
    return result




def test():


    device = usb.core.find(idVendor=0x5555, idProduct=0x5710)
    for el in device:
        print(el)
    
    print('channel: ', device.product)
    print('bus: ', device.bus)
    print('address: ', device.address)
    

    #try: 
    network = canopen.Network()

    #node = canopen.RemoteNode(1, 'D:\My_projects\python_projects\engine\src\M series_MOTOR(2).eds')
    #network.add_node(node)

    network.connect(bustype="canalystii", channel="0", bitrate=1000000)

    #network.scanner.search()
    # We may need to wait a short while here to allow all nodes to respond
    #time.sleep(0.05)
    #for node_id in network.scanner.nodes:
    #    print("Found node %d!" % node_id)

    

    #except Exception as err:
    #    print(err)
    

    #device_name = node.sdo['Device Type'].raw
    #print(device_name)

    #for obj in node.object_dictionary.values():
        #print('0x%X: %s' % (obj.index, obj.name))
        #if isinstance(obj, canopen.objectdictionary.Record):
            #for subobj in obj.values():
                #print('  %d: %s' % (subobj.subindex, subobj.name))
    





    #with can.interface.Bus() as bus:

    #    msg = can.Message(arbitration_id=0x601, data=[0x2F, 0x60, 0x60, 0x00, 0x01], is_extended_id=True)

    #    try:
    #        bus.send(msg)
    #        print(f"Message sent on {bus.channel_info}")
    #    except can.CanError:
    #        print("Message NOT sent")
    pass

def test_2():
    import usb.core
    import usb.backend.libusb1

    backend = usb.backend.libusb1.get_backend(find_library=lambda x: "C:\Windows\System32\libusb-1.0.dll")
    
    device = usb.core.find(idVendor=0x5555, idProduct=0x5710, backend=backend)
    for el in device:
        print(el)

    #bus = can.interface.Bus(bustype='canalystii',bitrate=1000000) 
        
    #print('product: ', device.product)
    #print('bus: ', device.bus)
    #print('address: ', device.address)

    #network = canopen.Network()
    #network.connect(bustype="canalystii", channel='0', bitrate=1000000)
    print(backend)
    dev = canalystii.CanalystDevice(bitrate=1000000)
    print(dev)

def test_x():
    expect_result = '1100111010011001'   #15 bit + 1 = 16-bit crc    polinom: 10000011001011111     0x1065F
    expect_result2 = '110011101001100'   #15-bit crc                 polinom: 1010010111100110      0xA5E6
    crc = ''
    i = 0
    polinom = "{0:b}".format(i)
    while crc != expect_result2:
        i+=1
        print("i:", i)
        polinom = "{0:b}".format(i)
        crc = crc_remainder('1010101010100000100', polinom, '0')
        print("crc: ",crc)

    
        
    res = crc_check('1010101010100000100', polinom, crc)
    print(res)
    print("polinom: ", polinom)


def show_frame(can_dataframe):
    print("DATAFRAME: ", end=' ')
    for byte in can_dataframe:
        print(hex(byte), end=' ')
    
    print("")




if __name__ == "__main__":

    #backend = usb.backend.libusb1.get_backend(find_library=lambda x: "C:\Windows\System32\libusb-1.0.dll")
    #device = usb.core.find(idVendor=0x5555, idProduct=0x5710)

    #if device is None:
    #        raise ValueError('Device not found')

    #device.set_configuration()


    control_word_0F = (0x2B, 0x40, 0x60, 0x00, 0x0F, 0x00)
    work_mode =     (0x2F, 0x60, 0x60, 0x00, 0x01)                      # work mode 1       
    actual_position = (0x40, 0x64, 0x60, 0x00)
    speed = (0x23, 0x81, 0x60, 0x00, 0xE8, 0x03, 0x00, 0x00)
    acceleration = (0x23, 0x83, 0x60, 0x00, 0x20, 0x4E, 0x00, 0x00)
    control_word_2F =  (0x2B, 0x40, 0x60, 0x00, 0x2F, 0x00)                # control word 2F      
    location_cash = (0x23, 0x7A, 0x60, 0x00, 0xE0, 0x93, 0x04, 0x00)    # location cash 300 000 = 0493E0
    status = (0x40, 0x41, 0x60, 0x00)



    package = SDO(1,data=location_cash)
    can_dataframe = package.build_can_dataframe()
    show_frame(can_dataframe)
    
    


    #can_dataframe = bytes(can_dataframe)
    #print("sending... ", can_dataframe)

    #written_bytes = device.write(0x01, can_dataframe)								
    #print("written_bytes: ", written_bytes)
    #time.sleep(1)
    #try:
    #    returned_bytes = device.read(0x83, written_bytes)					
    #    print("returned_bytes: ", returned_bytes)	
    #except Exception as err:
    #    print(err)
        

    #try:
    #    test_x()
    #except Exception as err:
    #    print(err)
    

