import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

# plt.plot([1, 2, 3, 4])
# plt.ylabel('some numbers')
hl, = plt.plot([1,2,3,4], [4,5,1,2])
plt.show()

plt.draw()