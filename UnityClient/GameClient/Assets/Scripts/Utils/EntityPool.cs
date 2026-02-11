using System.Collections.Generic;
using UnityEngine;

public class EntityPool : MonoBehaviour
{
    [SerializeField] private GameObject prefab;
    [SerializeField] private int preloadCount = 50;

    private readonly Queue<GameObject> _pool = new Queue<GameObject>();

    public static EntityPool Instance { get; private set; }

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;

        for (int i = 0; i < preloadCount; i++)
        {
            var go = Instantiate(prefab, transform);
            go.SetActive(false);
            _pool.Enqueue(go);
        }
    }

    public GameObject Get()
    {
        GameObject go;
        if (_pool.Count > 0)
        {
            go = _pool.Dequeue();
        }
        else
        {
            go = Instantiate(prefab, transform);
        }
        go.SetActive(true);
        return go;
    }

    public void Return(GameObject go)
    {
        go.SetActive(false);
        go.transform.SetParent(transform);
        _pool.Enqueue(go);
    }

    private void OnDestroy()
    {
        if (Instance == this) Instance = null;
    }
}
