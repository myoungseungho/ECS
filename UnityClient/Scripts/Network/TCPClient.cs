// ━━━ TCPClient.cs ━━━
// TCP 연결 + 패킷 송수신 (스레드 안전)
// 서버의 [4바이트 길이][2바이트 타입][페이로드] 프로토콜 처리

using System;
using System.Collections.Concurrent;
using System.Net.Sockets;
using System.Threading;

namespace Network
{
    /// <summary>수신된 패킷 (메인 스레드에서 처리할 큐 아이템)</summary>
    public struct ReceivedPacket
    {
        public MsgType Type;
        public byte[] Payload;
    }

    /// <summary>
    /// TCP 클라이언트. 별도 스레드에서 수신하고, 큐에 적재.
    /// Unity 메인 스레드에서 DequeueAll()로 꺼내서 처리.
    /// </summary>
    public class TCPClient : IDisposable
    {
        private TcpClient _client;
        private NetworkStream _stream;
        private Thread _recvThread;
        private volatile bool _running;

        // 수신 패킷 큐 (스레드 안전)
        private readonly ConcurrentQueue<ReceivedPacket> _recvQueue = new ConcurrentQueue<ReceivedPacket>();

        // 연결 상태
        public bool IsConnected => _client != null && _client.Connected && _running;

        // 이벤트
        public event Action OnDisconnected;

        /// <summary>서버에 TCP 연결</summary>
        public bool Connect(string host, int port, int timeoutMs = 5000)
        {
            try
            {
                _client = new TcpClient();
                var result = _client.BeginConnect(host, port, null, null);
                bool success = result.AsyncWaitHandle.WaitOne(timeoutMs);

                if (!success || !_client.Connected)
                {
                    _client.Close();
                    _client = null;
                    return false;
                }

                _client.EndConnect(result);
                _client.NoDelay = true;
                _stream = _client.GetStream();

                _running = true;
                _recvThread = new Thread(RecvLoop) { IsBackground = true };
                _recvThread.Start();

                return true;
            }
            catch
            {
                _client?.Close();
                _client = null;
                return false;
            }
        }

        /// <summary>패킷 전송</summary>
        public void Send(byte[] packet)
        {
            if (!IsConnected || _stream == null) return;

            try
            {
                _stream.Write(packet, 0, packet.Length);
            }
            catch
            {
                Disconnect();
            }
        }

        /// <summary>큐에 쌓인 수신 패킷을 모두 꺼냄 (메인 스레드에서 호출)</summary>
        public int DequeueAll(Action<MsgType, byte[]> handler)
        {
            int count = 0;
            while (_recvQueue.TryDequeue(out var pkt))
            {
                handler(pkt.Type, pkt.Payload);
                count++;
            }
            return count;
        }

        /// <summary>연결 종료</summary>
        public void Disconnect()
        {
            if (!_running) return;
            _running = false;

            try { _stream?.Close(); } catch { }
            try { _client?.Close(); } catch { }

            _stream = null;
            _client = null;

            OnDisconnected?.Invoke();
        }

        public void Dispose()
        {
            Disconnect();
        }

        // ━━━ 수신 스레드 ━━━

        private void RecvLoop()
        {
            byte[] headerBuf = new byte[PacketConst.HEADER_SIZE];

            try
            {
                while (_running && _stream != null)
                {
                    // 1. 헤더 읽기 (6바이트)
                    if (!ReadExact(headerBuf, PacketConst.HEADER_SIZE))
                        break;

                    uint totalLen = BitConverter.ToUInt32(headerBuf, 0);
                    ushort msgType = BitConverter.ToUInt16(headerBuf, 4);

                    // 유효성 검사
                    if (totalLen < PacketConst.HEADER_SIZE || totalLen > PacketConst.MAX_PACKET_SIZE)
                        break;

                    // 2. 페이로드 읽기
                    int payloadLen = (int)totalLen - PacketConst.HEADER_SIZE;
                    byte[] payload = null;

                    if (payloadLen > 0)
                    {
                        payload = new byte[payloadLen];
                        if (!ReadExact(payload, payloadLen))
                            break;
                    }
                    else
                    {
                        payload = Array.Empty<byte>();
                    }

                    // 3. 큐에 적재
                    _recvQueue.Enqueue(new ReceivedPacket
                    {
                        Type = (MsgType)msgType,
                        Payload = payload
                    });
                }
            }
            catch { }

            // 연결 종료
            if (_running)
                Disconnect();
        }

        /// <summary>정확히 N바이트 읽기 (TCP 스트림 특성상 여러 번 읽어야 할 수 있음)</summary>
        private bool ReadExact(byte[] buffer, int count)
        {
            int offset = 0;
            while (offset < count)
            {
                int read = _stream.Read(buffer, offset, count - offset);
                if (read <= 0) return false;
                offset += read;
            }
            return true;
        }
    }
}
