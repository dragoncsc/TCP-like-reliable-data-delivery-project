'''


event: ACK received, with ACK field value of y if (y > SendBase) {
SendBase=y
if (there are currently any not yet
acknowledged segments) start timer
}
else { /* a duplicate ACK for already ACKed
segment */
increment number of duplicate ACKs
received for y
if (number of duplicate ACKS received
for y==3)
/* TCP fast retransmit */
resend segment with sequence number y
} break;



	Figure out how to build header
		- http://www.binarytides.com/raw-socket-programming-in-python-linux/
	Hardcode timeout first to make sure actual sending and recieving works
	Hardcode window size to test sending and parsing of header

	Algo: pg 269
	ACK = seq # of next expected binarytides
	EstimatedRTT = (1-a)*EstimatedRTT + a*SampleRTT
	DevRTT = (1-B)*DevRTT + B*|SampleRTT - EstimatedRTT|
	TimeoutInterval = EstimatedRTT + 4*DevRTT

	Outline:
		- Data at Sender
			- How to handle new data?
				- chop up data into segment sizes intially?
					 - build headers and append at start for all?
					 	- Simple list/Array?
					 	- if I use array, need to map indicies in
					 		dictionary so that I can check for ACKs
					 	- Everytime window changes, update the dictionary
				- or just build segments as needed?
					- nah
			- Create segment, sequence #
			- NextSeqNum = NextSeqNum + Length(data)
			- start timer
		- ACK Recv w/val = y
			- if y > SendBase
				- SendBase = y
				- if ( there are unacked segments )
					- start timer
				- else:
					- stop timer
			- If sender recieves 3 ACKs for same data, resend unacked
				segment with smallest sequence number
		- Don't forget FIN at the end

'''

class stdout(object):
	def write(self, _input):
		print _input



import os
import socket
from struct import *
import time
import threading
import select
import sys

class TCPSender:

	def __init__(self, recvIP, remotePort, ACKport, fileName, logfile, windowSize=1):
		if logfile == 'stdout':
			self.log = stdout()
		else:
			self.log = open( logfile, 'w' )
		self.recvIP = recvIP
		self.ACKport = ACKport
		self.WS = windowSize
		self.remotePort = remotePort
		self.maxSegSize = 576
		self.timer = ('off', 0)
		self.timeOut = 1
		self.EstimatedRTT = 1
		self.DevRTT = .25
		self.ackseq_to_index = {}
		self.sentList = {}
		#self.ye = False
		# total file size being transferred
		self.size = 0

		# ALL DATA CHUNKS WITH HEADERS ARE STORED HERE, header is FIRST 32 chars
		self.dataSegments = []
		self.RTT_calc = {}
		# LIST OF ALL RETURNED ACKS, -1th element would be the last, IN ORDER, data segment
		# tuple of ACK number and number of times recieved
		self.ACks = []
		self.curWindow = (0, self.WS)
		self.cutFile( fileName )
		self.recvList = []


	def cutFile(self, fileName):
		'''
			import a file
			chunk file by segment size
			build all fields
			calculate checksum by adding all numbers as 16 bit integers
			figure out how to limit sum to 16 bits (wraparound)
			split file into 16 bit chucks (must be better way)
			add to sum
		'''
		with open( fileName, 'rb' ) as f:
			# calc checksum from all chunks of 576 byte packets, put into list
			# indexed by packet number (multiply this by 576)
			chunkList = self.calcFileBits( f , fileName)
			size = os.path.getsize(fileName)
			if size % self.maxSegSize == 0:
				fileIter = size/self.maxSegSize
			else:
				fileIter = size/self.maxSegSize + 1
			# use this for keeping track of the total size of file
			total_seq = 0
			for i in range(0, fileIter):
				_source = self.ACKport
				_dest = self.remotePort
				if i == fileIter - 1:
					#_seq = total_seq + size % self.maxSegSize
					_seq = i * self.maxSegSize
					_fin = 1
				else:
					_seq = i * self.maxSegSize
					total_seq += _seq
					_fin = 0
				_ack_seq = 0
				_offset = 5
				# garbage flags
				#_fin = 0
				_syn = 0
				_rst = 0
				_psh = 0
				_ack = 0
				_urg = 0
				# expected number of bytes + some amount of buffer for header + extra
				_windowSize = self.WS
				_urg_ptr = 0
				_unusedFlags = _fin + (_syn << 1) + (_rst << 2) + (_psh << 3) + (_ack << 4) + (_urg << 5)

				ack_mapping = _seq + 575
				self.ackseq_to_index[ack_mapping] = i

				# Calc checksum from all flags
				headSum = 0
				headSum = self.bitOverFlow(_source, _dest)
				headSum = self.bitOverFlow( headSum, _seq )
				headSum = self.bitOverFlow( headSum, _ack_seq)
				headSum = self.bitOverFlow( headSum, _offset)
				headSum = self.bitOverFlow( headSum, _unusedFlags)
				headSum = self.bitOverFlow( headSum, _syn)
				headSum = self.bitOverFlow( headSum, _windowSize)
				headSum = self.bitOverFlow( headSum, chunkList[i])
				# b = bin(headSum)
				b = format( headSum, '016b' )

				b = b.replace( '0', 'x' )
				b = b.replace( '1', '0' )
				b = b.replace( 'x', '1' )
				#b = b.replace( '1b', '0b')
				_check = int(b,2)
				bitHeader = pack( 'HHLLBBHHH', _source, _dest, _seq, _ack_seq, 
					_offset, _unusedFlags, _windowSize, _check, _urg_ptr )
				# store each segement as a tuple: (seg number, header + data)
				self.dataSegments[i] = ( _seq, bitHeader + self.dataSegments[i])

	# Control greater than 16 bits overflow
	# HEY!! CANNOT USE SUBTRACTION, GOTTA MOD/ KEEP REDUCING UNTIL BELOW 65535
	def bitOverFlow( self, num1, num2):
		num = num1 + num2
		if num > 65535:
			while num > 65535:
				num = num - 65536 + 1
		return num


	def calcFileBits( self, f , fileName):
		size = os.path.getsize(fileName)
		self.size = size
		bitSum = 0
		segChunks = []

		while True:
			# read MAX SEG SIZE
			block = f.read(576)
			# Check for EOF
			if block:
				self.dataSegments.append( block )
				bitSum = 0
				# compute on all chars of read data
				for char in block:
					bitSum = self.bitOverFlow( bitSum, ord(char) )
				segChunks.append( bitSum )
			else:
				break

		return segChunks


	'''
		send data, create UDP socket
		check if timer is on
		send all datagrams in range
		wait while timer is not out

		Issue:
			how to make sure sender sleeps after sending all packets in range, but 
			also make it able to send new packets that are in range (as ACKs come in)
		Solution:
			infinite loop, check to make sure timer is on ?? (should I get rid of this) ???
			send all messages in window range, but check to see if they have already been sent first
			( this allows the program to dynamically adjust the sent window without holding )
			if the timer exceeds the timeout limit, then empty the sent set

		Issue:
			How to know which packet caused timeout (and subsequently should be resent)
		Solution:
			Since window range is constantly being updated as ACKs come in, the packet that
			caused the ACK should probably be the smallest packet in the window range
			(IS THIS A SAFE ASSUMPTION??????? ANSWER NEEDED)
			when timeout occurs, just resend entire range

		Issue:
			This is really quite hard
		Solution:
			SHUT UP AND DANCE WITH ME

		Issue:
			How to format timer so that it restarts for every recently ACKed packet? I don't
			want to cause unnessary timeouts
		Solution:
			- Put sequence number in packet to identify which packet started timer?
			- Just call the startTimer() function from the forked function that recieves 
				packets?
			- Do i really ever need to keep track of sequence numbers (apart from curWindow)
				which just tracks indicies

		Issue:
			Client only sends ACK number to identify message, need a way to match that to an 
			index to update range
		Solution:
			client sends back ack with bit number up to which it has ACKed, when chopping up file,
			have a dictionary with ack_seq number as key and index as value.
			When data comes in, use this mapping to update curWindow

		Issue:
			triple duplicate ack situation
		Solution:
			just have three variables that keep track of last three indicies

		Issue:
			How to gracefully exit after successful completion?
		Solution:

	'''


	'''
		Basic process -->
		transferFile()
			fork out ACKreciever
			fork out sequenceCalc

			---------------------
			check curWindow
			send all packets
			check timeout

	- look out for faulty checksum generation!
	CURRENT ISSUE: i gets out of range when file transfer is complete, so I made a check for i before sending
			currently not sending any packets because cannot find i in data segments
	'''

	# simple create timer with tuple of 'on'/'off' variable and current time
	def startTimer(self):
		self.timer = ('on', time.time())


	# Loops infinitely, waiting for data, appending it to list which is read by another forked program
	def ACKreciever(self, transferComplete):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.bind( ( socket.gethostbyname(socket.gethostname()), self.ACKport ) )
		self.send2ACK = sock
		while True:
			# it would hold on this forever if I didn't check for complete transfer
			if not transferComplete.isSet():
				data, addr = sock.recvfrom(1024)
				self.recvList.append( data )
			if transferComplete.isSet():
				# file successfully transferred
				return

	# calc RTT
	def RTT( self, recv_tup, _time ):

		_ack = recv_tup[3]
		if _ack == 0:
			SampleRTT = 1
		else:
			SampleRTT = _time - self.RTT_calc[_ack-575]
		self.EstimatedRTT = ( .125 ) * self.EstimatedRTT + .875 * float(SampleRTT)

		self.DevRTT = ( .75 ) * self.DevRTT + .25 * abs( SampleRTT - self.EstimatedRTT )

		self.timeOut = self.EstimatedRTT + 4 * self.DevRTT
		return self.timeOut



	# header unpack value: (1234, 5000, 948, 0, 5, 2, 29186, 39640, 0)
	# ( source, dest port, seq, seq_ack, blah....)
	# self.last_ack is a stack where the head is the last recieved head
	def sequenceCalc(self, transferComplete):
		last_one = 0
		last_two = 1
		last_three = 2

		while True:
			# no new acks
			if len(self.recvList) < 1:
				continue
			last_ack = self.recvList.pop()
			recv_tup = unpack('HHLLBBHHH', last_ack)
			
			this_time = self.RTT( recv_tup, time.time() )

			# got ack num
			ack_seq = recv_tup[3]
			# convert to index number
			if ack_seq == 0:
				index = 0
			else:
				index = self.ackseq_to_index[ack_seq]
			#print 'recieved ack: ', ack_seq, '  mapped index:  ', index

			last_three = last_two
			last_two = last_one
			last_one = index

			# triple duplicate ACK implementation
			if last_one == last_two and last_two == last_three:
				# if this is true I'm seriously FUCKED
				if index != self.curWindow[0] and (index > self.curWindow[0] and index < self.curWindow[1]):
					self.curWindow = ( index, index+self.WS+1 )

				self.startTimer()
				self.sent = set( [ ] )
			# don't increment index if there was a trip duplicate ack!
			elif index >= self.curWindow[0] and index <= self.curWindow[1]:

				write = threading.Thread( target=self.write_to_file, args=( recv_tup, this_time) )
				write.setDaemon(True)
				write.start()
				# create new range to iterate over
				#self.write_to_file( recv_tup, this_time)
				self.curWindow = (index+1, index + 1 +self.WS)
			# FIN RECIEVED!!
				if recv_tup[5] & 1 == 1:
					transferComplete.set()
					return


	def write_to_file( self, recv_tup, this_time ):
		_log = self.log
		_time = str(time.time() )
		source = str( recv_tup[0])
		dest = str( recv_tup[1] )
		_seq = str( recv_tup[2] )
		_ack_ = str( recv_tup[3] )
		unused_f = recv_tup[5]
		_fin = str( unused_f & 1 )
		_syn = str( (unused_f >> 1) & 1 )
		_rst = str( (unused_f >> 2) & 1 )
		_psh = str( (unused_f >> 3) & 1 )
		_ack = str( (unused_f >> 4) & 1 )
		_ack = str( 1 )
		_urg = str( (unused_f >> 5) & 1 )
	
		_log.write( ' '.join([_time, source, dest, _seq, _ack_, _fin, _syn, _rst, _psh, _ack, _urg, str(this_time)]) )
		_log.write( '\n' )


	# fin loop
	def exitSeq( self, sock ):
		global _REMOTE_IP
		sock = self.send2ACK
		cur_time = time.time()
		while time.time() - cur_time < 5:
			print time.time() - cur_time
			rdy, l, k = select.select( [sock], [],[], .1 )
			for s in rdy:
				if s == sock:
					data = sock.recvfrom(1024)
					try:
						recv_tup = unpack('HHLLBBHHH', data[:32])
						if recv_tup[5] & 1 == 1:
							recv_tup = pack( 'HHLLBBHHH', recv_tup[0], recv_tup[1], recv_tup[2], recv_tup[3], recv_tup[4], 1, recv_tup[6], recv_tup[7], recv_tup[8] )
							sock.sendto( recv_tup, ( _REMOTE_IP, self.remotePort ) )
							return
					except:
						pass
		# timed out, return
		return


	# main driver for file transferring
	def tranferFile(self):
		global _REMOTE_PORT
		global _LOG_FILE
		# Internal communication mechanism between different threads
		# turn 'on' when file is successfully transferred

		transferComplete = threading.Event()
		ACKreciever = threading.Thread( target=self.ACKreciever, args=(transferComplete,) )
		ACKreciever.setDaemon(True)
		ACKreciever.start()
		sequenceCalc = threading.Thread( target=self.sequenceCalc, args=(transferComplete,) )
		sequenceCalc.setDaemon(True)
		sequenceCalc.start()
		
		s = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		s.bind( ( '', 5001 ) )
		self.sent  = set( [ ] )
		_repeat_counter = set( [] )
		_num_repeats = 0
		_total_count = 0
		while True:

			if transferComplete.isSet():
				__time = time.time()
				exitSequence = threading.Thread( target=self.exitSeq, args=(s,) )
				exitSequence.setDaemon(True)
				exitSequence.start()
				while time.time() - __time < 5.23:
					pass
				if _LOG_FILE != 'stdout':
					self.log.close()
				print 'Delivery completed successfully'
				print 'Total bytes sent = ', (_total_count * 576)
				print 'Segments sent = ', _total_count
				print 'Segments retransmitted = ', _num_repeats
				sys.exit()

			# turn on timer for timeout
			if self.timer[0] != 'on':
				self.startTimer()

			#to prevent iterating over range while updating curWindow
			start = self.curWindow[0]
			end = self.curWindow[1]
			for i in range( start, end ):

				# to prevent deleting self.sent WHILE iterating over it
				processed = list(self.sent)
				if i not in processed and not transferComplete.isSet() and i < len(self.dataSegments):
					if i in _repeat_counter:
						_num_repeats += 1
					self.RTT_calc[i*576] = time.time()
					_repeat_counter.add( i )
					_total_count += 1
					s.sendto( self.dataSegments[i][1], ( _REMOTE_IP, self.remotePort ) )
					self.sentList[ self.dataSegments[i][0] ] =  time.time()
					self.sent.add(i)

			# TIMEOUT so resend the range
			if time.time() - self.timer[1] > self.timeOut:
				self.sent  = set( [ ] )
				self.startTimer()




commandLine = sys.argv
_FILENAME = commandLine[1]
_REMOTE_IP = commandLine[2]
_REMOTE_PORT = int(commandLine[3])
_ACK_PORT = int(commandLine[4])
_LOG_FILE = commandLine[5]

_REMOTE_IP = socket.gethostbyname( _REMOTE_IP )

if len(sys.argv) == 7:
	_WINDOW_SIZE = int(commandLine[6])
	lol = TCPSender( _REMOTE_IP, _REMOTE_PORT, _ACK_PORT, _FILENAME, _LOG_FILE, _WINDOW_SIZE )
else:
	lol = TCPSender( _REMOTE_IP, _REMOTE_PORT, _ACK_PORT, _FILENAME, _LOG_FILE )



#recvIP, remotePort, ACKport, fileName, windowSize=1
#lol = TCPSender( 1234567890, 41192, 1234, 'Programming+Assignment+2.pdf', 4 )
#lol = TCPSender( 1234567890, 41192, 1234, 'test.txt', 5 )
#lol = TCPSender( 1234567890, 41192, 1234, 'PA1.pptx', 20 )
#lol = TCPSender( 1234567890, 41192, 1234, 'Chapter_2_V6.1_(4).ppt', 5 )


lol.tranferFile()



'''

	Description of exit sequence:
		- In __init__, the last packet gets a FIN bit set
		- in transferFile, the last packet is sent normally and waits for ACK confirmation
		- Client sees FIN bit set, goes into shutdown mode, sends ack for last packet
		- In ACKreciever, client's ACK is loaded into recvList, FIN read in sequenceCalc,
			transferComplete is set which notifies all other functions
			- ACKreciever exits
		- transferFile goes into completion --> exitSeq
			- quickly build new socket to listen on to ACKport, listen for last FIN.
			- when recieved, exit


'''