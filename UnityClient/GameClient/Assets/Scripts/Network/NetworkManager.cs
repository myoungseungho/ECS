// ━━━ NetworkManager.cs ━━━
// Unity MonoBehaviour로 작동하는 네트워크 매니저
// Gate → Field 연결 + 로그인 + 게임 진입 전체 파이프라인
// 수신 패킷을 Update()에서 처리 (메인 스레드 보장)

using System;
using System.Collections.Generic;
using UnityEngine;

namespace Network
{
    public class NetworkManager : MonoBehaviour
    {
        // ━━━ 설정 ━━━
        [Header("Server Settings")]
        public string GateHost = "127.0.0.1";
        public int GatePort = 8888;

        // ━━━ 상태 ━━━
        public enum ConnectionState
        {
            Disconnected,
            ConnectingGate,
            ConnectingField,
            LoggingIn,
            CharSelect,
            InGame,
        }

        public ConnectionState State { get; private set; } = ConnectionState.Disconnected;
        public ulong MyEntityId { get; private set; }
        public int CurrentZone { get; private set; }
        public int CurrentChannel { get; private set; }

        // ━━━ TCP 클라이언트 ━━━
        private TCPClient _gate;
        private TCPClient _field;

        // 현재 활성 연결
        private TCPClient ActiveClient => _field ?? _gate;

        // ━━━ 이벤트 (UI/게임 로직이 구독) ━━━
        public event Action<LoginResult, uint> OnLoginResult;
        public event Action<CharacterInfo[]> OnCharacterList;
        public event Action<EnterGameResult> OnEnterGame;
        public event Action<ulong, float, float, float> OnEntityAppear;
        public event Action<ulong> OnEntityDisappear;
        public event Action<ulong, float, float, float> OnEntityMove;
        public event Action<int> OnZoneChanged;
        public event Action<int> OnChannelChanged;
        public event Action<StatSyncData> OnStatSync;
        public event Action<AttackResultData> OnAttackResult;
        public event Action<CombatDiedData> OnCombatDied;
        public event Action<RespawnResultData> OnRespawnResult;
        public event Action<MonsterSpawnData> OnMonsterSpawn;
        public event Action<MonsterRespawnData> OnMonsterRespawn;
        public event Action<string> OnError;
        public event Action OnDisconnected;

        // ━━━ 싱글톤 ━━━
        public static NetworkManager Instance { get; private set; }

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        private void OnDestroy()
        {
            _gate?.Dispose();
            _field?.Dispose();
            if (Instance == this) Instance = null;
        }

        // ━━━ Update: 수신 패킷 처리 (메인 스레드) ━━━

        private void Update()
        {
            _gate?.DequeueAll(HandleGatePacket);
            _field?.DequeueAll(HandleFieldPacket);
        }

        // ━━━ 공개 API ━━━

        /// <summary>1단계: Gate 서버 연결 → 자동으로 GATE_ROUTE_REQ 전송</summary>
        public void ConnectToGate()
        {
            State = ConnectionState.ConnectingGate;
            _gate = new TCPClient();
            _gate.OnDisconnected += () => { /* Gate는 1회용이라 무시 */ };

            if (!_gate.Connect(GateHost, GatePort))
            {
                OnError?.Invoke("Gate 서버 연결 실패");
                State = ConnectionState.Disconnected;
                return;
            }

            Debug.Log($"[Net] Gate 연결 성공 ({GateHost}:{GatePort})");
            _gate.Send(PacketBuilder.GateRouteReq());
        }

        /// <summary>3단계: 로그인</summary>
        public void Login(string username, string password)
        {
            if (_field == null || !_field.IsConnected)
            {
                OnError?.Invoke("Field 서버에 연결되지 않음");
                return;
            }

            State = ConnectionState.LoggingIn;
            _field.Send(PacketBuilder.Login(username, password));
        }

        /// <summary>4단계: 캐릭터 목록 요청</summary>
        public void RequestCharList()
        {
            _field?.Send(PacketBuilder.CharListReq());
        }

        /// <summary>5단계: 캐릭터 선택</summary>
        public void SelectCharacter(uint charId)
        {
            State = ConnectionState.CharSelect;
            _field?.Send(PacketBuilder.CharSelect(charId));
        }

        /// <summary>6단계: 채널 입장</summary>
        public void JoinChannel(int channelId)
        {
            CurrentChannel = channelId;
            _field?.Send(PacketBuilder.ChannelJoin(channelId));
        }

        /// <summary>이동 전송</summary>
        public void SendMove(float x, float y, float z)
        {
            _field?.Send(PacketBuilder.Move(x, y, z));
        }

        /// <summary>존 이동</summary>
        public void EnterZone(int zoneId)
        {
            _field?.Send(PacketBuilder.ZoneEnter(zoneId));
        }

        /// <summary>스탯 동기화 요청</summary>
        public void RequestStatSync()
        {
            _field?.Send(PacketBuilder.StatQuery());
        }

        /// <summary>공격 요청</summary>
        public void SendAttack(ulong targetEntityId)
        {
            _field?.Send(PacketBuilder.AttackReq(targetEntityId));
        }

        /// <summary>부활 요청</summary>
        public void RequestRespawn()
        {
            _field?.Send(PacketBuilder.RespawnReq());
        }

        /// <summary>Gate 없이 Field 서버에 직접 연결</summary>
        public void ConnectDirect(string host, int port)
        {
            ConnectToField(host, port);
        }

        /// <summary>연결 끊기</summary>
        public void DisconnectAll()
        {
            _gate?.Dispose();
            _field?.Dispose();
            _gate = null;
            _field = null;
            State = ConnectionState.Disconnected;
        }

        // ━━━ Gate 패킷 핸들러 ━━━

        private void HandleGatePacket(MsgType type, byte[] payload)
        {
            if (type == MsgType.GATE_ROUTE_RESP)
            {
                var route = PacketBuilder.ParseGateRouteResp(payload);
                if (route.ResultCode != 0)
                {
                    OnError?.Invoke("Gate 라우팅 실패");
                    State = ConnectionState.Disconnected;
                    return;
                }

                Debug.Log($"[Net] Gate → Field {route.IP}:{route.Port}");

                // Gate 연결 닫기
                _gate.Dispose();
                _gate = null;

                // Field 연결
                ConnectToField(route.IP, route.Port);
            }
        }

        // ━━━ Field 연결 ━━━

        private void ConnectToField(string host, int port)
        {
            State = ConnectionState.ConnectingField;
            _field = new TCPClient();
            _field.OnDisconnected += () =>
            {
                State = ConnectionState.Disconnected;
                OnDisconnected?.Invoke();
            };

            if (!_field.Connect(host, port))
            {
                OnError?.Invoke($"Field 서버 연결 실패 ({host}:{port})");
                State = ConnectionState.Disconnected;
                return;
            }

            Debug.Log($"[Net] Field 연결 성공 ({host}:{port})");
            // 이제 Login() 호출 가능
            State = ConnectionState.ConnectingField; // Login 대기
        }

        // ━━━ Field 패킷 핸들러 ━━━

        private void HandleFieldPacket(MsgType type, byte[] payload)
        {
            switch (type)
            {
                case MsgType.LOGIN_RESULT:
                {
                    var (result, accountId) = PacketBuilder.ParseLoginResult(payload);
                    Debug.Log($"[Net] Login result: {result}, accountId: {accountId}");
                    OnLoginResult?.Invoke(result, accountId);
                    break;
                }

                case MsgType.CHAR_LIST_RESP:
                {
                    var chars = PacketBuilder.ParseCharListResp(payload);
                    Debug.Log($"[Net] Character list: {chars.Length} characters");
                    OnCharacterList?.Invoke(chars);
                    break;
                }

                case MsgType.ENTER_GAME:
                {
                    var r = PacketBuilder.ParseEnterGame(payload);
                    if (r.ResultCode == 0)
                    {
                        MyEntityId = r.EntityId;
                        CurrentZone = r.ZoneId;
                        State = ConnectionState.InGame;
                        Debug.Log($"[Net] Enter game: entity={r.EntityId}, zone={r.ZoneId}, pos=({r.X},{r.Y},{r.Z})");
                    }
                    OnEnterGame?.Invoke(r);
                    break;
                }

                case MsgType.APPEAR:
                {
                    var (eid, x, y, z) = PacketBuilder.ParseEntityPosition(payload);
                    if (eid != MyEntityId) // 자기 자신은 무시
                        OnEntityAppear?.Invoke(eid, x, y, z);
                    break;
                }

                case MsgType.DISAPPEAR:
                {
                    ulong eid = PacketBuilder.ParseDisappear(payload);
                    if (eid != MyEntityId)
                        OnEntityDisappear?.Invoke(eid);
                    break;
                }

                case MsgType.MOVE_BROADCAST:
                {
                    var (eid, x, y, z) = PacketBuilder.ParseEntityPosition(payload);
                    if (eid != MyEntityId)
                        OnEntityMove?.Invoke(eid, x, y, z);
                    break;
                }

                case MsgType.ZONE_INFO:
                {
                    int zoneId = PacketBuilder.ParseIntResponse(payload);
                    CurrentZone = zoneId;
                    Debug.Log($"[Net] Zone changed: {zoneId}");
                    OnZoneChanged?.Invoke(zoneId);
                    break;
                }

                case MsgType.CHANNEL_INFO:
                {
                    int chId = PacketBuilder.ParseIntResponse(payload);
                    CurrentChannel = chId;
                    Debug.Log($"[Net] Channel: {chId}");
                    OnChannelChanged?.Invoke(chId);
                    break;
                }

                case MsgType.STAT_SYNC:
                {
                    var data = PacketBuilder.ParseStatSync(payload);
                    Debug.Log($"[Net] StatSync: Lv{data.Level} HP={data.HP}/{data.MaxHP}");
                    OnStatSync?.Invoke(data);
                    break;
                }

                case MsgType.ATTACK_RESULT:
                {
                    var data = PacketBuilder.ParseAttackResult(payload);
                    Debug.Log($"[Net] AttackResult: {data.Result}, dmg={data.Damage}, target HP={data.TargetHP}/{data.TargetMaxHP}");
                    OnAttackResult?.Invoke(data);
                    break;
                }

                case MsgType.COMBAT_DIED:
                {
                    var data = PacketBuilder.ParseCombatDied(payload);
                    Debug.Log($"[Net] CombatDied: dead={data.DeadEntityId}, killer={data.KillerEntityId}");
                    OnCombatDied?.Invoke(data);
                    break;
                }

                case MsgType.RESPAWN_RESULT:
                {
                    var data = PacketBuilder.ParseRespawnResult(payload);
                    Debug.Log($"[Net] RespawnResult: result={data.ResultCode}, HP={data.HP}, pos=({data.X},{data.Y},{data.Z})");
                    OnRespawnResult?.Invoke(data);
                    break;
                }

                case MsgType.MONSTER_SPAWN:
                {
                    var data = PacketBuilder.ParseMonsterSpawn(payload);
                    Debug.Log($"[Net] MonsterSpawn: entity={data.EntityId}, monsterId={data.MonsterId}, lv={data.Level}, hp={data.HP}/{data.MaxHP}");
                    OnMonsterSpawn?.Invoke(data);
                    break;
                }

                case MsgType.MONSTER_RESPAWN:
                {
                    var data = PacketBuilder.ParseMonsterRespawn(payload);
                    Debug.Log($"[Net] MonsterRespawn: entity={data.EntityId}, hp={data.HP}/{data.MaxHP}");
                    OnMonsterRespawn?.Invoke(data);
                    break;
                }

                default:
                    Debug.Log($"[Net] Unknown packet: type={type}, len={payload.Length}");
                    break;
            }
        }
    }
}
