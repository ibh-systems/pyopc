# zip ps format
cp PyOPC.ps temp.ps
gzip temp.ps
mv temp.ps.gz PyOPC.ps.gz

scp -r index.html html PyOPC.ps.gz PyOPC.pdf dusty128@ssh.sourceforge.net:htdocs/docs/ 
