import socket
from socket import *
from struct import *
import Queue
import threading
import time
import select
import sys


class stdout(object):
	def write(self, _input):
		print _input

'''

	Issue:
		How to properly implement reciever range and check it
	Solution:
		Well the sender already sends it's range, so we can just use that
		we can keep track of all well formatted data segments in that range
		
		Idea: use 'two' tuple to list the range of accepted ACK numbers, if the
			incoming data is in that range, then accept it, otherwise, resend last 
			ACK
			Additionally, keep last successful ACK on hand ALWAYS

	What do I want to do right now:
		Checking for inorder delivery of packets
	How I'm doing it:
		first check for correctly recieved packet?? Maybe not because this is a wasted operation
		--> Better: get packet, unpack header, have a temp variable that stores the last ACK seq
				if cur seq number is (last_seq_num + 575), then that means this is the next packet
				in order! Then continue with all checking
				--> one thing: initialize last seqnum to be something negative (normally impossible)
					so that we know that this is the first packet

	Issue: 
		How to deal with out of order segments?
	Solution:
		compare last acked header to current header, if it is 576 greater, then this is next packet
		in stream, if not, then discard (wasteful, yes)
'''



'''
REMEMBER TO FIGURE OUT SWITCH TO STDOUT
'''
def write_to_log( recv_tup, _log_file):
	_time = str( time.time() - __time_start )
	# (1234, 5000, 948, 0, 5, 2, 29186, 39640, 0)
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
	_urg = str( (unused_f >> 5) & 1 )

	_log_file.write( ' '.join([_time, source, dest, _seq, _ack_, _fin, _syn, _rst, _psh, _ack, _urg]) )
	_log_file.write( '\n' )
	
	_ack_ = str( recv_tup[2] + 575 )
	_log_file.write( ' '.join([_time, source, dest, _seq, _ack_, _fin, _syn, _rst, _psh, str(1), _urg]) )
	_log_file.write( '\n' )


# Control greater than 16 bits overflow
def bitOverFlow( num1, num2):
	num = num1 + num2
	if num > 65535:
		while num > 65535:
			num = num - 65536 + 1
	return num


#	Files are coming in super hot! gotta fork out to recieve the incoming packets
def getData(sock, queuedData, log_file):
	correctly_recv = {}
	fileFinished = threading.Event()
	checkData = threading.Thread( target=readData, args=(queuedData, correctly_recv, fileFinished, log_file) )
	checkData.start()
	#_newsock = 

	while True:		

		if fileFinished.isSet():
			break
		rdy, l, k = select.select( [sock], [],[], .1 )
		for s in rdy:
			if fileFinished.isSet():
				break
			if s == sock:
				data, addr = sock.recvfrom(1024)
				queuedData.put( data )



# look for corruptions in packet
def calcChecksum( data, correctly_recv ):
	totalSum = 0
	sumA = 0
	endOfPacket = False
	# what walks through the packet, 16 bits at a time
	bitPointer = 0
	l_ack = data[:32]
	datum =  data[32:]
	recv_tup = unpack('HHLLBBHHH', l_ack )
	
	for val in recv_tup: 
		totalSum = bitOverFlow( totalSum, val )

	while bitPointer < len(datum):
		block = datum[bitPointer]
		totalSum = bitOverFlow( totalSum, ord(block) )
		sumA = bitOverFlow( sumA, ord(block) )
		bitPointer += 1

	# whoops
	if totalSum == 65535:# or totalSum == 65535:
		return True
	else:
		#print totalSum
		return False

# make sure incoming files are in correct range
def checkWindow( recv_tup, curWindow, prev_header):

	# first segment sent
	if prev_header == 0 and recv_tup[2] == 0:
		return True
	if prev_header == 0 and recv_tup[2] != 0:
		return False


	# packet is greater than last recieved packet and less than window size
	if recv_tup[2] > prev_header[2] and recv_tup[2] <= prev_header[2] + 576 * curWindow:
		return True
	else:
		#print '-------> LOLSKIS <--------'
		return False


def writeToFile( f, fileDict ):

	all_seqs = fileDict.keys()
	all_seqs = sorted(all_seqs)
	#print all_seqs
	#print len(all_seqs)
	for key in all_seqs:
		f.write( fileDict[key] )

	f.close()


def exitSequence( f, fileDict, recv_tup ):
	global _SENDERIP
	global sock
	global _SENDERPORT

	writeToFile( f, fileDict )
	_time = time.time()
	
	send_this_shit = pack( 'HHLLBBHHH', recv_tup[0], recv_tup[1], recv_tup[3],
		 recv_tup[2]+575, recv_tup[4], recv_tup[5], recv_tup[6], recv_tup[7], recv_tup[8] )
	sock.sendto( send_this_shit, (_SENDERIP, _SENDERPORT) )
	
	send_this_shit = pack( 'HHLLBBHHH', recv_tup[0], recv_tup[1], recv_tup[3],
		 0, recv_tup[4], 1, recv_tup[6], recv_tup[7], recv_tup[8] )

	while time.time() - _time  < 5:
		#print time.time() - _time
		sock.sendto( send_this_shit, ( _SENDERIP, _SENDERPORT ) )
		rdy, l, k = select.select( [sock], [],[], .1 )
		for s in rdy:
			if s == sock:
				data, addr = sock.recvfrom(1024)
				recv_tup = unpack('HHLLBBHHH', data[:32])
				if recv_tup[5] & 1 == 1:
					print 'Delivery completed successfully'
					sys.exit()
	sys.exit()



def readData( queuedData, correctly_recv, fileFinished, log_file):
	#try:
		# implement recv window checking here
		global _SENDERIP
		global _SENDERPORT
		global _NEWFILENAME
		oneSent = False
		if log_file == 'stdout':
			_log = stdout()
		else:
			_log = open( log_file, 'w' )
		f = open( _NEWFILENAME, 'w' )
		fileDict = {}
		temp = ''
		i = 0
		prev = ''
		cur = ''
		rest = ''
		curWindow = 0
		prev_header = 0
		_port = 0
		while True:
			# if there is new data to be processed
			if queuedData.qsize() > 0:
				data = queuedData.get()
				oneSent = True

				last_ack = data[:32]
				rest = data[32:]
				recv_tup = unpack('HHLLBBHHH', last_ack)

				_already_sent = False
				# already got it
				if recv_tup[2] in fileDict:
					recv_tup = prev_header
					_already_sent = True
					#print recv_tup[2]
					#continue
			

				# Idea: the first packet can get corrupted, so set curWindow to 0 at first and check
				# ack number sent across, then if packet passes checksum test, update curWindow only once
				# to the first packet's value
				# NEED TO MAKE SURE THIS IS ALSO FIRST packet
				if not _already_sent:
					checkVal = calcChecksum( data, correctly_recv )

					if curWindow == 0 and checkVal:
						curWindow = recv_tup[6]
						_port = recv_tup[0]

					# packet is inside recv window and has right checksum
					if not checkWindow( recv_tup , curWindow, prev_header ) or not checkVal:
						#print 'CORRUPTED OR OUT OF WINDOW RANGE'
						recv_tup = prev_header

					# FIN bit set
					elif prev_header != 0 and prev_header[2] + 576 == recv_tup[2] and recv_tup[5]&1 == 1:
						#print 'WELLLLLL RECIEVED PACKET'
						fileFinished.set()

						write = threading.Thread( target=write_to_log, args=( recv_tup, _log) )
						write.setDaemon(True)
						write.start()
						#write_to_log( recv_tup, _log )
						prev_header = recv_tup
						fileDict[ recv_tup[2] ] = rest
						exitSequence(  f, fileDict ,recv_tup )
					# deal with first packet in stream
					elif prev_header == 0 and recv_tup[2] == 0:
						#print 'WELLLLLL RECIEVED PACKET'

						write = threading.Thread( target=write_to_log, args=( recv_tup, _log) )
						write.setDaemon(True)
						write.start()
						#write_to_log( recv_tup, _log )
						fileDict[ recv_tup[2] ] = rest
						prev_header = recv_tup
					# If this was the next inorder packet
					elif prev_header[2] + 576 == recv_tup[2]:
						#print 'WELLLLLL RECIEVED PACKET'
						write_to_log( recv_tup, _log )
						prev_header = recv_tup
						fileDict[ recv_tup[2] ] = rest
					# out of order segment
					else:
						recv_tup = prev_header

				# replace the seq number with the ack number
				if recv_tup != 0:
					pass
					#print ' recieved seq number:  ', recv_tup[2]
				else:
					print 'corruption on first packet'
					continue
				send_this_shit = pack( 'HHLLBBHHH', recv_tup[0], recv_tup[1], recv_tup[3],
					 recv_tup[2]+575, recv_tup[4], recv_tup[5], recv_tup[6], recv_tup[7], recv_tup[8] )
				sock.sendto( send_this_shit, ( _SENDERIP, _SENDERPORT ) )

			elif not oneSent or prev_header == 0:
				continue
			else:
				recv_tup = prev_header
				#print 'In if statement, recieved seq number:  ', recv_tup[2]
				send_this_shit = pack( 'HHLLBBHHH', recv_tup[0], recv_tup[1], recv_tup[3],
					 recv_tup[2]+575, recv_tup[4], recv_tup[5], recv_tup[6], recv_tup[7], recv_tup[8] )
				sock.sendto( send_this_shit, ( _SENDERIP, _SENDERPORT ) )

			prev_header = recv_tup



commandLine = sys.argv
_NEWFILENAME = commandLine[1]
_LISTENINGPORT = int(commandLine[2])
_SENDERIP = commandLine[3]
_SENDERPORT = int(commandLine[4])
_LOGFILENAME = commandLine[5]


_SENDERIP = gethostbyname( _SENDERIP )

__time_start = time.time()

sock = socket(AF_INET, SOCK_DGRAM)
sock.bind( ( gethostbyname(gethostname()) , _LISTENINGPORT) )
print gethostbyname(gethostname())
queuedData = Queue.Queue()

getData( sock, queuedData, _LOGFILENAME )


















