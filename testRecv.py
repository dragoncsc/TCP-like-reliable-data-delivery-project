import socket
import time



print 'done sleeping'

s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
s.bind( ('localhost', 1234) )

s.listen(1)

conn, addr = s.accept()

data = conn.recv( 1024 )

conn.send( data )

conn.close()