from ctypes import windll,wintypes,pointer
from ctypes import windll
def max_win():
	GetWindowRect=windll.user32.GetWindowRect
	FindWindowW=windll.user32.FindWindowW
	GetSystemMetrics=windll.user32.GetSystemMetrics
	max_win_id=FindWindowW("Shell_TrayWnd",None)
	rect=wintypes.RECT()
	GetWindowRect(max_win_id, pointer(rect))
	max_win=(rect.left, rect.top, rect.right, rect.bottom)
	if max_win[0]==0 and max_win[1]==0 and max_win[2]==GetSystemMetrics(0):
	    max_win=(0,max_win[3],max_win[2],windll.user32.GetSystemMetrics(1))
	elif max_win[0]==0 and max_win[1]==0 and max_win[3]==GetSystemMetrics(1):
	    max_win=(max_win[2],0,GetSystemMetrics(0),max_win[3])
	elif max_win[0]==0 and max_win[1]>0:
	    max_win=(0,0,max_win[2],max_win[1])
	elif max_win[0]>0 and max_win[1]==0:
	    max_win=(0,0,max_win[0],max_win[3])
	return max_win
if __name__ == '__main__':
	print(max_win())