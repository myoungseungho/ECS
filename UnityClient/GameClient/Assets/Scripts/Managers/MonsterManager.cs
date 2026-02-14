// ━━━ MonsterManager.cs ━━━
// 몬스터 엔티티 생명주기 관리
// NetworkManager 이벤트 구독 → 몬스터 생성/파괴/이동/HP 갱신

using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class MonsterManager : MonoBehaviour
{
    [Header("Prefabs")]
    [SerializeField] private GameObject monsterPrefab;

    // Entity ID → MonsterEntity
    private readonly Dictionary<ulong, MonsterEntity> _monsterMap = new Dictionary<ulong, MonsterEntity>();

    public IReadOnlyDictionary<ulong, MonsterEntity> MonsterMap => _monsterMap;

    // ━━━ 이벤트 ━━━
    public event Action<MonsterEntity> OnMonsterSpawned;
    public event Action<ulong> OnMonsterDied;
    public event Action<MonsterEntity> OnMonsterUpdated;
    public event Action<ulong, ulong> OnMonsterAggroChanged;   // monsterEntity, targetEntity (0=해제)

    // ━━━ 싱글톤 (Scene-bound) ━━━
    public static MonsterManager Instance { get; private set; }

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
        net.OnMonsterSpawn += HandleMonsterSpawn;
        net.OnMonsterRespawn += HandleMonsterRespawn;
        net.OnCombatDied += HandleCombatDied;
        net.OnEntityMove += HandleEntityMove;
        net.OnAttackResult += HandleAttackResult;
        net.OnDisconnected += HandleDisconnected;
        net.OnMonsterMove += HandleMonsterMove;
        net.OnMonsterAggro += HandleMonsterAggro;
    }

    private void OnDestroy()
    {
        var net = NetworkManager.Instance;
        if (net == null) return;

        net.OnMonsterSpawn -= HandleMonsterSpawn;
        net.OnMonsterRespawn -= HandleMonsterRespawn;
        net.OnCombatDied -= HandleCombatDied;
        net.OnEntityMove -= HandleEntityMove;
        net.OnAttackResult -= HandleAttackResult;
        net.OnDisconnected -= HandleDisconnected;
        net.OnMonsterMove -= HandleMonsterMove;
        net.OnMonsterAggro -= HandleMonsterAggro;

        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>Entity ID로 몬스터 조회 (없으면 null)</summary>
    public MonsterEntity GetMonster(ulong entityId)
    {
        _monsterMap.TryGetValue(entityId, out var monster);
        return monster;
    }

    /// <summary>해당 Entity ID가 몬스터인지 확인</summary>
    public bool IsMonster(ulong entityId)
    {
        return _monsterMap.ContainsKey(entityId);
    }

    // ━━━ 핸들러 ━━━

    private void HandleMonsterSpawn(MonsterSpawnData data)
    {
        if (_monsterMap.ContainsKey(data.EntityId))
        {
            // 이미 존재하면 갱신
            var existing = _monsterMap[data.EntityId];
            Vector3 pos = CoordConverter.ServerToUnity(data.X, data.Y);
            existing.Initialize(data.EntityId, data.MonsterId, data.Level, data.HP, data.MaxHP, pos);
            existing.gameObject.SetActive(true);
            OnMonsterUpdated?.Invoke(existing);
            return;
        }

        Vector3 spawnPos = CoordConverter.ServerToUnity(data.X, data.Y);

        GameObject go;
        if (monsterPrefab != null)
            go = Instantiate(monsterPrefab, spawnPos, Quaternion.identity);
        else
            go = CreateDefaultMonster(spawnPos);

        var monster = go.GetComponent<MonsterEntity>();
        if (monster == null)
            monster = go.AddComponent<MonsterEntity>();

        monster.Initialize(data.EntityId, data.MonsterId, data.Level, data.HP, data.MaxHP, spawnPos);
        _monsterMap[data.EntityId] = monster;

        // World UI (HP bar + name)
        var worldUI = go.GetComponent<MonsterWorldUI>();
        if (worldUI == null)
            worldUI = go.AddComponent<MonsterWorldUI>();
        worldUI.Initialize(monster);

        Debug.Log($"[MonsterManager] Spawn: entity={data.EntityId}, monsterId={data.MonsterId}, lv={data.Level}, hp={data.HP}/{data.MaxHP}");
        OnMonsterSpawned?.Invoke(monster);
    }

    private void HandleMonsterRespawn(MonsterRespawnData data)
    {
        Vector3 pos = CoordConverter.ServerToUnity(data.X, data.Y);

        if (_monsterMap.TryGetValue(data.EntityId, out var monster))
        {
            monster.HP = data.HP;
            monster.MaxHP = data.MaxHP;
            monster.SetTargetPosition(pos);
            monster.transform.position = pos;
            monster.gameObject.SetActive(true);

            Debug.Log($"[MonsterManager] Respawn: entity={data.EntityId}, hp={data.HP}/{data.MaxHP}");
            OnMonsterUpdated?.Invoke(monster);
        }
        else
        {
            Debug.LogWarning($"[MonsterManager] Respawn 대상 없음: entity={data.EntityId}");
        }
    }

    private void HandleCombatDied(CombatDiedData data)
    {
        if (!_monsterMap.TryGetValue(data.DeadEntityId, out var monster)) return;

        monster.HP = 0;
        monster.PlayDeath();

        Debug.Log($"[MonsterManager] Died: entity={data.DeadEntityId}, killer={data.KillerEntityId}");
        OnMonsterDied?.Invoke(data.DeadEntityId);

        StartCoroutine(DelayedDeactivate(monster.gameObject, 2f));
    }

    private IEnumerator DelayedDeactivate(GameObject go, float delay)
    {
        yield return new WaitForSeconds(delay);
        if (go != null)
            go.SetActive(false);
    }

    private void HandleEntityMove(ulong entityId, float x, float y, float z)
    {
        if (!_monsterMap.TryGetValue(entityId, out var monster)) return;

        Vector3 pos = CoordConverter.ServerToUnity(x, y);
        monster.SetTargetPosition(pos);
    }

    private void HandleAttackResult(AttackResultData data)
    {
        // 공격 대상이 몬스터면 HP 갱신 + 피격 애니메이션
        if (!_monsterMap.TryGetValue(data.TargetId, out var monster)) return;

        monster.HP = data.TargetHP;
        monster.MaxHP = data.TargetMaxHP;
        monster.PlayHit(0f);
        OnMonsterUpdated?.Invoke(monster);
    }

    private void HandleDisconnected()
    {
        foreach (var kvp in _monsterMap)
        {
            if (kvp.Value != null && kvp.Value.gameObject != null)
                Destroy(kvp.Value.gameObject);
        }
        _monsterMap.Clear();
    }

    private void HandleMonsterMove(MonsterMoveData data)
    {
        if (!_monsterMap.TryGetValue(data.EntityId, out var monster)) return;

        Vector3 pos = CoordConverter.ServerToUnity(data.X, data.Y);
        monster.SetTargetPosition(pos);
    }

    private void HandleMonsterAggro(MonsterAggroData data)
    {
        OnMonsterAggroChanged?.Invoke(data.MonsterEntityId, data.TargetEntityId);
    }

    // ━━━ 유틸 ━━━

    /// <summary>Prefab 없을 때 기본 몬스터 오브젝트 생성 (빨간 큐브)</summary>
    private static GameObject CreateDefaultMonster(Vector3 pos)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.transform.position = pos;
        go.transform.localScale = new Vector3(0.8f, 0.8f, 0.8f);

        var renderer = go.GetComponent<MeshRenderer>();
        if (renderer != null)
        {
            var mat = new Material(renderer.sharedMaterial);
            mat.color = new Color(0.9f, 0.2f, 0.2f);
            renderer.material = mat;
        }

        return go;
    }
}
