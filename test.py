
'''
nonBinarysum = 0
Binarysum = 0



kk = set( [] )

with open('Programming+Assignment+2.pdf', 'rb') as f:
	while True:

		block = f.read(576)
		if block:
			# Binarysum += ord(block)
			print hash(block) & 65534
			if hash(block) & 65534 in kk :
				print 'REPEAT!!!!!!!!!!!!!!!'
			kk.add( hash(block) & 65534 )
		else:
			break
'''



'''
with open('Programming+Assignment+2.pdf', 'r') as f:
	lolskis = f.read()

for char in lolskis:
	nonBinarysum += ord(char)

print type(lolskis)
print nonBinarysum
print Binarysum
'''



f = open( 'stdin', 'w')
f.write( 'lolskis' )















