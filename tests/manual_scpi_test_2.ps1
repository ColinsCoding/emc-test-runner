$client = $null
$stream = $null
$writer = $null
$reader = $null

try {
  $client = New-Object System.Net.Sockets.TcpClient("127.0.0.1", 5025)
  $stream = $client.GetStream()

  $writer = New-Object System.IO.StreamWriter($stream)
  $writer.AutoFlush = $true

  $reader = New-Object System.IO.StreamReader($stream)

  $writer.WriteLine("*IDN?")
  $reader.ReadLine()

} finally {
  if ($reader) { $reader.Dispose() }
  if ($writer) { $writer.Dispose() }
  if ($stream) { $stream.Dispose() }
  if ($client) { $client.Close(); $client.Dispose() }
}
