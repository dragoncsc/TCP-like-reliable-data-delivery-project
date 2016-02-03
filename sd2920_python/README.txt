

IMPORTANT NOTES CONCERNING MY IMPLEMENTATION:
	- My Sender program sends packets from port 5001, and receives ACK packets on the port specified in the command line. For this reason, when using the proxy to forward packets, make sure to use 5001 as the port on the sender side. The project description did not specify which port/from where the sender should send packets so I randomly chose this port.
	
	- Log files: the client log files have time stamps that correspond to the time since the program has been running (in seconds). The Sender log file has timestamps since epoch using time.time(). I did this because on Piazza, no one specified what the timestamp should be. Additionally, the sender side has the RTT time that helps with contextualizing how long the program is taking while the Client log file just has the amount of time since the client program started for contextualization.




For this project, I used python to implement reliable, inorder delivery file service.

Here is an example of how to run the client:
python Client.py shit.txt 5005 269.31.194.436 1234 stdout

Here is an example of how to run the Server:
python Sender.py test.txt 140.34.124.336 5005 1234 stdout 7

I successfully implemented the 20 byte TCP header format, using the struct module to pack and unpack the 
header. When I packed the header on the server side, I concatinate the file to the end of the header.

Here is the command to 'pack' the header into it's bit format: 
bitHeader = pack( 'HHLLBBHHH', _source, _dest, _seq, _ack_seq, _offset, _unusedFlags, _windowSize, _check, _urg_ptr )'HHLLBBHHH' is the format of the bits. H stands for short int (2 bytes), L stands for int (4 bytes) B is binary (1 byte)

I calculate the checksum by summing all the header fields first, then reading the file byte by for the maximum segment
size of each packet. Then I cast each byte to a number using the ord() function and summing up all the bytes in the 
packet. Every time the sum value surpasses 65535, I subtract 65536 from the sum and add 1 (to simulate wraparound).
Then I add the data sum to the header sum, checking for wrap around, and used the bin() function to cast it into a binary
string. I switched all the 1s with 0s and all the 0s with 1s to simulate XORing the string, then pass this value to the
header. On the client side, I do the same thing by summing all the values of the header and then reading the data bit by
bit. If my total sum equals 65535, I know the packet is corruption free.

My delivery service discards out of order packets. On my client side, I have three different threads running at the same time. One reads data from the socket and appends it to a thread safe queue, another is constantly checking the thread safe queue, calculating the checksum on tha packet, adding correct, inorder, packets to a dictionary, and sending ACKs with the ack number of the packet. When the client reads a fin bit from the sender, it gets all the keys of the dictionary with all the acked data in it, sorts the keys (the keys are the ack sequence number of the packets), and then appends the data to the specified output file, calling the keys on the dictionary in increasing order. Then, it sends an ack for the final fin, enters a loop that counts to 5 seconds, and sends a fin bit of its own. if the sender sends a fin bit while the client is in the 5 second loop, the client closes all its sockets and gracefully exits. else, it finished the 5 seconds of waiting and exits.

On the sender side, my program first chunks the file into 588 byte chunks, then calculates the header as described before and stores all the packets in a dictionary indexed by packet number # relative to the size of the file. The last packet gets a fin bit in its header. It inditializes the window in the __init__ method (from 0 to window size) and then starts sendign all packets in that range. when a packet is sent in that range, its index is put in a set(), so that the same packet will not be resent, unless the timeout limit is reached and the set() is reset to empty. every time a packet is sent, it is added to a dictionary, where the seq number is the key and the time it was sent is the value. In another thread, whenever an ack comes in, my program uses the last sent packet time with that sequence number, and the time the packet arrived to calculate the RTT time. I ahve another thread constantly looking for acks to update the current window size. When the last packet is sent and an ack is recieved, my program goes into an exit state where it waits for the last ACK, then enters a 5 second loop waiting for a fin from the client. if it gets the fin, my program closes all relevant files and sockets and exits. if it doesn't get the fin bit, it waits the 5 seconds, then closes all relevant files and sockets and exits.

Loss recovery mechanism: On the client side, I keep a variable that stores the last successfully acked packet header. I pop the front of the queue and I check it’s check sum value, if that fails, I send an ack for the previous packet (that was corruption free and in order). If it passes the checksum, but is greater than the last asked packet’s sequence number + 1 + MAX SEGEMENT SIZE, I send an ack for the previous packet. If all was successful, I send an ack for this packet, putting the packet’s sequence number+MAX SEGMENT SIZE as the ack number. If it was the last packet (with a fin bit) I ack the packet and go into my exit loop where the client sends its own fin bit. 
On the sender side, I have a timer running (estimated by the equation given in the textbook and the individual RTT times). While the timer is not out, I send all the packets in the current range ONCE and wait. When acks arrive, I assume they are for all the bits up till the ack number. I have a dictionary that maps ack numbers to index values of the list of all data segments and get the acked packet’s index. from there, I update the cur window by index + 1.



My program works reasonably for files up to 2.5 mb (gets really slow), on my computer, but starts slowing down around 100Kb on clic machines. My program is not very efficient and discards way too many packets. additioanlly it has a huge memory overhead, but it does work. On thing to look out for is that if there are a lot of bit corruptions, it takes a while to ack the first packet so it seems like my program is doing nothing. additionally, I printed out the count down of the sender and client programs end states so that the TAs will not think that my program stalled. it is a matter of convenience. The write/reads work well.































