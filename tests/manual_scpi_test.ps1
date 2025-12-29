$client = New-Object System.Net.Sockets.TcpClient("127.0.0.1",5025)
$stream = $client.GetStream()
$writer = New-Object System.IO.StreamWriter($stream)
$writer.AutoFlush = $true
$reader = New-Object System.IO.StreamReader($stream)

$writer.WriteLine("*IDN?")
$reader.ReadLine()

$writer.WriteLine("*OPC?")
$reader.ReadLine()

$writer.WriteLine("SYST:ERR?")
$reader.ReadLine()

$client.Close()
