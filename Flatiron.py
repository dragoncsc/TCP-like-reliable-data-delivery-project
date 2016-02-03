# you can write to stdout for debugging purposes, e.g.
# print "this is a debug message"
'''
def solution(A):
    # write your code in Python 2.7
    sum = 0
    temp = {}
    for i in range(0, len(A)):
        temp[i] = sum
        sum += A[i]
    sum = 0
    i = len(A)-1
    while( i>= 0):
        temp[i] = (temp[i], sum)
        sum += A[i]
        i = i -1
    bool = False
    for i in range( 0, len(A) ):
        if i == 0:
            if temp[i][1] == 0:
                print i
                bool = True
                #return i
        elif i == len(A)-1:
            if temp[i][0] == 0:
                #return i
                bool = True
                print i
        elif temp[i][0] == temp[i][1]:
            #return i
            bool = True
            print i
    #return -1
    if bool != True:
        print -1
    
    return


A = [-1, 3, -4, 5, 1, -6, 2, 1]
solution(A)
'''
def solution(S):
    # write your code in Python 2.7
    numbers = {}
    total_time = 0
    l_sent = S.split()
    calls = {}
    curMax = 0
    i = 0
    for line in l_sent:
        number = line.split(',')[1]
        if number not in numbers:
            numbers[number] = 0
        temp_time = line.split(',')[0].split(':')
        
        time = int(temp_time[0]) * 3600
        time += int(temp_time[1]) * 60
        time += int(temp_time[2])

        calls[i] = (number, time)
        numbers[number] += time
        i += 1
    
    key_num = calls.keys()
    cost = 0

    for k in key_num:
        if calls[k][1] < 300:
            cost += calls[k][1] * 3
        else :
            if calls[k][1] % 60 != 0:
                cost += ((int(calls[k][1])/60) + 1) * 150
            else:
                cost += (int(calls[k][1])/60) * 150

    maxCall = []
    maxC = 0
    for phNu in numbers:
        if numbers[phNu] > maxC:
            maxCall = [phNu]
            maxC = numbers[phNu]
        elif numbers[phNu] == maxC:
            maxCall.append(phNu)

    if len(maxCall) > 1:
        maxCall.sort()

    maxNum = maxCall[0]


    val = 0
    for call in calls:
        if calls[call][0] == maxNum:        
            if calls[call][1] < 300:
                val += calls[call][1] * 3
            if calls[call][1] >= 300:
                if calls[call][1] % 60 != 0:
                    val += ((calls[call][1]/60) + 1) * 150
                else:
                    val += (calls[call][1]/60) *150

    cost = cost - val
    return cost





S = '00:01:07,400-234-090\n00:05:01,701-080-080\n00:05:00,400-234-090'

print solution(S)



