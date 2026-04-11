# 获取 WSL IP
$wslIP = (wsl hostname -I).Trim()
# 删除旧规则
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0
netsh interface portproxy delete v4tov4 listenport=5173 listenaddress=0.0.0.0
# 添加端口转发
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=$wslIP
netsh interface portproxy add v4tov4 listenport=5173 listenaddress=0.0.0.0 connectport=5173 connectaddress=$wslIP
Write-Host "WSL IP: $wslIP"
Write-Host "端口转发已设置"