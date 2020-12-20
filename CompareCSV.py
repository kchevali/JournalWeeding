def format_array(a):
    for i in range(len(a)):
        a[i] = a[i].split(";")
        for j in range(len(a[i])):
            a[i][j] = a[i][j].replace("\n","").replace("|","").lower()
    return a
        

def find_title(title,array):
    for j in range(len(b)):
        if title == b[j][2]:
            return j
    return None

def find_matching(a,b):
    index = []
    for i in range(len(a)):
        title = a[i][2][4:] if a[i][2][:4] == "the " else a[i][2]
        if len(title) > 0 and title[0] <= 'l'[0]:
            j = find_title(a[i][2],b)
            if j == None:
                print(a[i][2],end=", ")
            else:
                index.append((i,j))
    print("\n")
    return index

a = format_array(open("OnlineWeedList.csv",'r').readlines())
b = format_array(open("OnlineWeedList2.csv",'r').readlines())

print("Theresa is missing: ",end="")
matches = find_matching(a,b)
print("Kevin is missing: ",end="")
find_matching(b,a)

labels = ["Call #","Librarian","TITLE","WEED ISSUES","Available Online","PL Microfiche Holdings","Online Collection"]
for i in matches:
    for j in range(7):
        if a[i[0]][j] != b[i[1]][j]:
            print("Incorrect " + labels[j] + " for " + a[i[0]][2] + ":\n\t'" + a[i[0]][j] + "' & '" + b[i[1]][j] + "'")
