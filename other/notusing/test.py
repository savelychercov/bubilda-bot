from random import randint

measure = {
    1: "см", 
    100: "м", 
    1_000: "км",
    1_737_400: "рад. Луны",
    6_356_863: "рад. Земли",
    299_792_458: "св. сек",
    149_597_870_700: "аст. ед",
    9_460_730_472_580_800: "св. год"
    }

def shorten(num: int):
    last = 1
    for i in measure.keys():
        if num >= i: last = i

    total = round(num/last, 2)
    if total - round(total) == 0: total = round(total)

    return str(total)+" "+measure[last]

count = 0

def get_random_height1():
    while True:
        temp = randint(-5, 10)
        if temp: return temp

def get_random_height2():
    if randint(0, 3):
        return randint(1, 10)
    else:
        return randint(-5, -1)
    
def get_random_height3(height):
    mx = int(height/10)+1
    mn = -mx//2
    if mx < 10: mx = 10
    return randint(mn, mx)

for i in range(365):
    temp = get_random_height3(count)
    print(((("+ " if temp > 0 else "- ")+shorten(abs(temp))).ljust(20)+"| "+shorten(count)).ljust(45)+"| "+str(i))
    count+=temp

print("\n"+shorten(count))