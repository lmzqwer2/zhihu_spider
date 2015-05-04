@echo off
set /p v=number of spiders: 
for /l %%i in (1,1,%v%) do (
	start python spider.py -a=http://lmin.me:8004 -c=1
)