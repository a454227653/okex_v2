
def func(s):
  s_spl = s.split(' ')
  temp = []
  for word in s_spl:
    if word!=' ' and len(word)>0:
      temp.append(word)
  res=''
  for word in temp:
    if word[0]>='A' and word[0]<='Z':
      res+='\n'
    res+=word
    res+=' '
  return res

s='let  us.   haVe. Fun For 11.11!'
res = func(s)
print(res)