import sys

def Bbasis(i, p, u, uk):

  a, b = 0, 0

  if (p == 0): 
    return 1 if (u >= uk[i] and u < uk[i+1]) else 0
  else:
    if (uk[i+p] != uk[i]):
      a = (u-uk[i])/(uk[i+p]-uk[i])*Bbasis(i,p-1,u,uk)
    if (uk[i+p+1] != uk[i+1]):
      b = (uk[i+p+1]-u)/(uk[i+p+1]-uk[i+1])*Bbasis(i+1,p-1,u,uk)

  return a+b

def Bspline(n, cP, p, uk):

  curvePx = []
  curvePy = []

  cParr = []
  for key in cP:
    cParr.append(cP[key])

  for i in range(n-1):
    u = i/(n-1)

    sumX, sumY = 0, 0
    for j, (cpx, cpy) in enumerate(zip(cParr[0],cParr[1])):
      sumX += Bbasis(j,p,u,uk)*cpx 
      sumY += Bbasis(j,p,u,uk)*cpy

    curvePx.append(sumX)
    curvePy.append(sumY)

  curvePx.append(cParr[0][-1])
  curvePy.append(cParr[1][-1])

  return {"x": curvePx , "y": curvePy}

def BsplineFit(x, nCp, p, uk):
  
  n = len(x)
  u = [(i+1)/(n-1) for i in range(n-2)]

  Q = [x[i+1]-Bbasis(0,p,u[i],uk)*x[0]-
      Bbasis(nCp-1,p,u[i],uk)*x[n-1] for i in range(n-2)]

  A = []
  b = []
  for k in range(nCp-2):
    Al = []
    for l in range(nCp-2):
      Al.append(0)
      for i in range(n-2):
        Al[l] += Bbasis(l+1,p,u[i],uk)*Bbasis(k+1,p,u[i],uk)
    A.append(Al)

    b.append(0)
    for i in range(n-2):
      b[k] += Q[i]*Bbasis(k+1,p,u[i],uk)
    
  a = Gauss(A,b)
  return [x[0], *a, x[n-1]]

def Gauss(A, b):
  m = len(A)

  for row in A:
    if len(row) != m:
      sys.exit('A is not a square matrix')

  if len(b) != m:
    sys.exit('Sizes of A and b are not compatible')

  Ab = []
  for i, value in enumerate(b):
    Ab.append([*A[i], value])

  for i in range(0, m-1):
    max = i

    for j in range(i+1, m):
      if(abs(Ab[j][i]) > abs(Ab[max][i])):
        max = j

    Ab[i], Ab[max] = Ab[max], Ab[i]

    if (abs(Ab[i][i]) <= sys.float_info.min):
      sys.exit('Singular or nearly singular matrix')

    for j in range(i+1, m):
      alpha = Ab[j][i] / Ab[i][i]

      for k in range(i, m+1):
        Ab[j][k] -= alpha*Ab[i][k]

  if (abs(Ab[m-1][m-1]) <= sys.float_info.min):
    sys.exit('Singular or nearly singular matrix')

  x = [0 for i in range(0, m)]
  for i in reversed(range(0, m)):
    sum = 0

    for j in range(i+1, m):
      sum += Ab[i][j] * x[j]

    x[i] = (Ab[i][m]-sum)/Ab[i][i]

  return x

