import sys
import numpy as np
import difflib

# 算法说明：
# 1 用矩阵存储所有aa/bb中字符串比较的相似度
# 2 相似度 * 100，用整数表示；计算权重时相似度>RATIO_SIMILAR视为相同
# 3 权重计算从右下单元开始向左上角[0,0]，根据自己的匹配度，行进方向和对应方向（右、下、右下）单元的权重计算而得
# 4 路径搜索从左上单元[0,0]开始到右下角，每步根据相似度、各方向[右（插入）、下（删除）、右下（相等）]单元权重选择路径
# 
# ratio_x: keep the original match ratio
# match_x: ratio match，1: match, 0: not. ratio > RATIO_SIMILAR is similar or equal
# weight_x: weight of the cell, include the rest of the path
#  +----------+--------+      
#  + current  ←   up  |     calculate weight of cell[current]
#  +---↑----↖--------+     = max(match[current]+weight[cross],     # if current match, the match will only effect when go cross
#  +  left  | cross  |            weight[up],    # go cell[up] or cell[left] the match[current] wight wonn't effect
#  +-------+--------+            weight[left])   # max() means sellect one of three direction to gain maxium weight in total
#
# path_x: direction r-go right, d-go down, e/s/c-go cross/right-down
#  +----------+--------+    from current cell select one of three direction to form path
#  + current →  right |     - head to biggest weight, or 
#  +----↓---↘-------+      - current cell is match or similar = cross, depends on ratio
#  +  down  | cross |       - down first (means delete line in aa)
#  +-------+-------+
#
# return difflib like operation code list, 
#   with one of 4 op type: e/s/d/i for equal/similar/delete/insert and i/i1, j/j1 for position
#   each operation is effect only one line
def diff_lines(aa:list[str], bb:list[str], RATIO_SIMILAR = 40):
    len_aa = len(aa)
    len_bb = len(bb)

    # compare each a&b and store ratio to matrix
    ratio_x = np.zeros((len_aa+1, len_bb+1), dtype=int)  # +1 for boundary element
    for i in range(len_aa):
        for j in range(len_bb):
            df_ab = difflib.SequenceMatcher(None, aa[i], bb[j])
            ratio_x[i][j] = int(100 * df_ab.ratio())

    # create match matrix
    match_x = np.where(ratio_x > RATIO_SIMILAR, 1, 0)  # ratio > RATIO_SIMILAR = similar, should be replace each other
    # print(f"\nmatch:\n{match_x}")
    
    #create weight matrix
    weight_x = np.zeros((len_aa+1, len_bb+1), dtype=int)

    # create path matrix
    path_x = np.empty((len_aa, len_bb), dtype="str")
    path_x.fill("")
    
    # calculate weight from bottom-right to top-left
    i = len_aa - 1
    j = len_bb - 1
    while True:
        #print(f"while i,j = {i},{j}")
        def cell4(m, n):  # calculate [m,n] weight acroding 4 cell's data(weight and match)
            #print(f"cell4 [m,n] = {m},{n}")
            c4 = weight_x[m:m+2, n:n+2]      # slice 2x2 array
            #print(c4)
            u = c4[0,1]    # [ ?  |  u ]
            l = c4[1,0]    # [ l  |  c ]
            c = c4[1,1]
            c4[0,0] = max(match_x[m, n] + c, l, u)   # key point of the algorithm
            
            # print(f"c4[]=\n{c4}\n -- ulc = {u},{l},{c} --- mn = {m},{n}")
            # end cell4
        
        cell4(i, j)                   # current cell
        for c in range(j-1, -1, -1):  # left line
            cell4(i, c)
        for c in range(i-1, -1, -1):  # up line
            cell4(c, j)

        if i == 0 and j == 0:
            break;  # quit while
        
        if i > 0: i -= 1
        if j > 0: j -= 1
    #end while

    # print(f"\nweight:\n{weight_x}")

    # calculate path from top-left to bottom-right
    i = 0
    j = 0
    ops = []
    while True:
        u = weight_x[i, j+1]    # [ ?  |  u ] 
        l = weight_x[i+1, j]    # [ l  |  c ]
        c = weight_x[i+1, j+1]

        # generate path
        if u == l == c:            # same weight
            if ratio_x[i,j] == 100:
                path_x[i,j] = "e"      # equal, go cross
            elif ratio_x[i,j] > RATIO_SIMILAR:
                path_x[i,j] = "s"      # similar, go cross
            else:
                path_x[i,j] = "d"      # go down first(delete the line in a)
        elif u>l and u>c:          # one is bigger than other two
            path_x[i,j] = "r"
        elif l>u and l>c: 
            path_x[i,j] = "d"
        elif c>u and c>l: 
            print("error, never be here")   # this wonn't happen acording the algorithm
            sys.exit()
        elif u>c and l>c:               # two bigger than other one, go down first
            path_x[i,j] = "d"
        elif c == l or c == u:                    # wonn't happen, c is never bigger than u or l
            raise RuntimeError("c never gigger than u or l")
        else:
            raise RuntimeError("never be here")
        # print(f"path_x[i,j]=[{i},{j}] -- ucl = {u},{l},{c} - path = {path_x[i,j]}")

        # form operation code list
        op = path_x[i,j]
        if op == "e" or op == "s":
            ops.append([op, i,i+1, j,j+1])  # equal/similar
            i += 1
            j += 1
        elif op == "d":
            ops.append(["d", i,i+1, j,j])  # delete for go down
            i += 1
        elif op == "r":
            ops.append(["i", i,i, j,j+1])  # insert for go right
            j += 1
        else:
            raise ValueError("never be here")

        all_done = False
        while i == len_aa or j == len_bb:  # touch the boundary
            if i == len_aa and j == len_bb:    # if reach the right-bottom conor
                all_done = True
                break  # quit while
                
            if i == len_aa:                      # touch bottom
                path_x[len_aa -1, j] = "r"
                ops.append(["i", i,i, j,j+1])  # go right = insert
                j += 1
            elif j == len_bb:                    # touch right
                path_x[i, len_bb-1] = "d"
                ops.append(["d", i,i+1, j,j])  # go down = delete
                i += 1
            else:
                raise AssertionError("never be here")
        if all_done:
            break   # quit while

        if i>= len_aa or j>= len_bb:
            raise AssertionError("never be here")
    # end while

    # for debug
    if False:
        print(f"\nratio_x :\n{ratio_x}")
        print(f"\nmatch_x :\n{match_x}")
        print(f"\nweight_x :\n{weight_x}")
        print(f"\npath_x :\n{path_x}")
    
        weight_xstr = weight_x.astype(str)
        weight_xs = weight_xstr[:-1, :-1]
    
        print(weight_xs)
    
        print(type(weight_xs), type(path_x))
        print(weight_xs.shape, path_x.shape)
    
        pw = np.core.defchararray.add(path_x, weight_xs)
    
        print(f"\nw&p: \n{pw}")
        print(f"\nops\n{ops}")

    return ops
#end of difflines



# build the line list from list1(original), list2(refined), change_op(operation code)
# input: list1, list2, change_op
#   operation code is follow the difflib.SequenceMatcher definition
#   op[0](e/s/d/i for equal/similar/delete/insert, 
#   op[1:2]=i1,i1 for list1 position, op[3:4]=j1,j2 for list 2 position
# output: line list combined with list1 and list2 with change mark(equal/similar/delete/insert)
#   [type(e/s/d/i), str], if s, str use "\n" to separate 2 lines(original and refined)
#   if type is "s", add another cell for inline ops[op, str]
def combine_changed_lines(list1:list[str], list2:list[str], change_op):
    result = []
    list1.append("")    #dummy line for append after lastline
    list2.append("")
    
    for op_code, i1, i2, j1, j2 in change_op:
        # print(f"{op_code} : {i1},{i2},{j1},{j2}")
        if op_code == "e":
            result.append(["e", list1[i1], ""])   # equal
            #print(list1[i1])
        elif op_code == "s":                 # similar
            str_op = diff_str(list1[i1], list2[j1]);
            result.append(["s",list1[i1] +"\n" + list2[j1], str_op])  # to be parse later
        elif op_code == "d":
            result.append(["d",list1[i1], ""])   # delete
            #print(list1[i1])
        elif op_code == "i":
            result.append(["i", list2[j1], ""])  # insert
            #print(list2[j1])
        else:
            raise ValueError(f"current op_code: {op_code}")     #error should not happen
    return result


# compare two string, output operation list to identify changes
# return operation code list,
#   with one of 3 op types: e/d/i (equal/delete/insert) and string
#   each operation may effect to multi characters
def diff_str(s1:str, s2:str):
    seq_mat = difflib.SequenceMatcher(a=s1, b=s2, autojunk=True)
    op = seq_mat.get_opcodes()
    
    result = []

    # print(f"\n\diff_str() input:--\n{s1}\n--\n{s2}\n")
    
    for operation, i1,i2,j1,j2 in op:
        #print(f"inside string: {operation},{i1},{i2},{j1},{j2},")
        if operation == "delete":
            result.append(["d", s1[i1:i2]])
        elif operation == "replace":       # 先显示删除内容，再显示更新内容
            result.append(["d", s1[i1:i2]])
            result.append(["i", s2[j1:j2]])
        elif operation == "insert":
            result.append(["i", s2[j1:j2]])
        elif operation == "equal":
            result.append(["e", s1[i1:i2]])

    # print(result)

    return result


# change one line op and string to html
# input: list[op, str] - one element means one line
#        highlight the line or the first changed element inside line
# output: string with html tag to mark out delete(<del>), insert(<strong>)
# 
def change_oneline_to_html(line, hilight = False) -> str:
    def equal(s):
        return f"<span style='color: #222222; {bg}'>{s}</span>"
    def delete(s):
        return f"<del style='color: red; {bg}'>{s}</del>"
    def insert(s):
        return f"<strong style='color: green; {bg}'>{s}</strong>"
    result = ""
    
    if hilight:
        bg = "background-color: yellow"
    else:
        bg = ""

    # print(line)

    if line[0] == "e":
        result = result + equal(line[1])
    elif line[0] == "d":
        result = result + delete(line[1])
    elif line[0] == "i":
        result = result + insert(line[1])
    elif line[0] == "s":                 # similar
        result = result + change_inline_op_to_html(line[2], hilight)
    else:
        raise ValueError("never ve here")
    return result


# change lines to html
# input: [op, str]
def change_inline_op_to_html(lines, hilight_first = False) -> str:
    def equal(s):
        return s
    def delete(s):
        return f"<del style='color: red;{bg}'>{s}</del>"
    def insert(s):
        return f"<strong style='color: green;{bg}'>{s}</strong>"
    result = ""
    
    is_first = True
    result = ""

    for line in lines:
        if is_first and hilight_first:
            bg = "background-color: yellow"
        else:
            bg = ""

        if line[0] == "e":
            result = result + equal(line[1])
        elif line[0] == "d":
            result = result + delete(line[1])
            is_first = False
        elif line[0] == "i":
            result = result + insert(line[1])
            is_first = False
        elif line[0] == "s":                 # no similar inline
            raise ValueError("wrong line[0] = {line[0]}")
        else:                                # bad op-code
            raise ValueError("wrong line[0] = {line[0]}")
    return result

def change_lines_to_html(lines):
    s = ""
    for line in lines:
        s = s + change_oneline_to_html(line) + "<br/>"
    return s