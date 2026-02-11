using System.Collections.Generic;
using UnityEngine;
using Network;

public class EntityManager : MonoBehaviour
{
    [Header("Prefabs")]
    [SerializeField] private GameObject localPlayerPrefab;
    [SerializeField] private GameObject remotePlayerPrefab;

    [Header("Settings")]
    [SerializeField] private bool usePooling = true;

    // 서버 Entity ID -> Unity GameObject
    private readonly Dictionary<ulong, GameObject> _entityMap = new Dictionary<ulong, GameObject>();

    public IReadOnlyDictionary<ulong, GameObject> EntityMap => _entityMap;

    private GameObject _localPlayer;
    public GameObject LocalPlayer => _localPlayer;

    public static EntityManager Instance { get; private set; }

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
    }

    private void Start()
    {
        var net = NetworkManager.Instance;

        net.OnEnterGame += OnEnterGame;
        net.OnEntityAppear += OnEntityAppear;
        net.OnEntityDisappear += OnEntityDisappear;
        net.OnEntityMove += OnEntityMove;
        net.OnDisconnected += OnDisconnected;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnEnterGame -= OnEnterGame;
        net.OnEntityAppear -= OnEntityAppear;
        net.OnEntityDisappear -= OnEntityDisappear;
        net.OnEntityMove -= OnEntityMove;
        net.OnDisconnected -= OnDisconnected;
    }

    private void OnEnterGame(EnterGameResult result)
    {
        if (result.ResultCode != 0) return;

        Vector3 spawnPos = CoordConverter.ServerToUnity(result.X, result.Y);

        _localPlayer = Instantiate(localPlayerPrefab, spawnPos, Quaternion.identity);
        _localPlayer.name = "LocalPlayer";

        var local = _localPlayer.GetComponent<LocalPlayer>();
        if (local != null)
            local.EntityId = result.EntityId;

        _entityMap[result.EntityId] = _localPlayer;
        Debug.Log($"[EntityManager] 내 캐릭터 생성: entity={result.EntityId}, pos={spawnPos}");
    }

    private void OnEntityAppear(ulong entityId, float x, float y, float z)
    {
        if (_entityMap.ContainsKey(entityId)) return;

        Vector3 pos = CoordConverter.ServerToUnity(x, y);

        GameObject go;
        if (usePooling && EntityPool.Instance != null)
            go = EntityPool.Instance.Get();
        else
            go = Instantiate(remotePlayerPrefab);

        go.transform.position = pos;
        go.name = $"Remote_{entityId}";

        var remote = go.GetComponent<RemotePlayer>();
        if (remote != null)
        {
            remote.EntityId = entityId;
            remote.SetTargetPosition(pos);
        }

        _entityMap[entityId] = go;
    }

    private void OnEntityDisappear(ulong entityId)
    {
        if (!_entityMap.TryGetValue(entityId, out var go)) return;

        _entityMap.Remove(entityId);

        if (usePooling && EntityPool.Instance != null)
            EntityPool.Instance.Return(go);
        else
            Destroy(go);
    }

    private void OnEntityMove(ulong entityId, float x, float y, float z)
    {
        if (!_entityMap.TryGetValue(entityId, out var go)) return;

        Vector3 pos = CoordConverter.ServerToUnity(x, y);

        var remote = go.GetComponent<RemotePlayer>();
        if (remote != null)
            remote.SetTargetPosition(pos);
    }

    private void OnDisconnected()
    {
        // 모든 엔티티 정리
        foreach (var kvp in _entityMap)
        {
            if (kvp.Value != null)
                Destroy(kvp.Value);
        }
        _entityMap.Clear();
        _localPlayer = null;
    }
}
