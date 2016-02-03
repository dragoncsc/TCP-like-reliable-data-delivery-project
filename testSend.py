import socket
import time


s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )

s.connect(  ('localhost', 1234)  )

s.send(  'FUCK YOU BITCH'  )

data = s.recv( 1024 )

print data


s.close()