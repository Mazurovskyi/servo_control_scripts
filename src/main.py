from src.lib.can_pkgs import SDO
from src.lib import can_pkgs
import usb.core
import usb.backend.libusb1
import time
import sys
from src.lib.decoder import Decode


backend = usb.backend.libusb1.get_backend(find_library=lambda x: "C:\Windows\System32\libusb-1.0.dll")
device = usb.core.find(idVendor=0x5555, idProduct=0x5710,backend=backend)

if device is None:
		raise ValueError('Device not found')

device.set_configuration()


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

returned_msg = Decode()

for data in dataframe:

	package = SDO(1,data=data)

	can_dataframe = package.build_can_dataframe()
	can_pkgs.show_frame(can_dataframe)
		

	#can_dataframe.reverse()

	#invert_can_dataframe = []
	#for byte in can_dataframe:
	#	invert_can_dataframe.append( ~byte & 0xFF)


	can_dataframe = bytes(can_dataframe)

	print("sending... ", can_dataframe)
	written_bytes = device.write(0x01, can_dataframe)								
	print("written_bytes: ", written_bytes)

	time.sleep(1)

	try:
		returned_bytes = device.read(0x83, 15)					
		print("returned_bytes: ", returned_bytes, "\n")	
		returned_msg.add(returned_bytes)
	except Exception as err:
		print(err)


returned_msg.save()		#save returned bytes into file
usb.util.dispose_resources(device)