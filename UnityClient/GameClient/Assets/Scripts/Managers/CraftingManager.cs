// ━━━ CraftingManager.cs ━━━
// 제작/요리/인챈트 시스템 관리 (S043 TASK 2)
// MsgType: 380-383 (제작), 386-387 (요리), 388-389 (인챈트)

using System;
using System.Collections.Generic;
using UnityEngine;

public class CraftingManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static CraftingManager Instance { get; private set; }

    // ━━━ 상태 ━━━
    private List<Network.CraftRecipeInfo> _recipes = new List<Network.CraftRecipeInfo>();
    private bool _isPanelOpen;

    // ━━━ 프로퍼티 ━━━
    public IReadOnlyList<Network.CraftRecipeInfo> Recipes => _recipes;
    public bool IsPanelOpen => _isPanelOpen;

    // ━━━ 이벤트 ━━━
    public event Action OnRecipeListChanged;
    public event Action<Network.CraftResultData> OnCraftComplete;
    public event Action<Network.CookResultData> OnCookComplete;
    public event Action<Network.EnchantResultData> OnEnchantComplete;
    public event Action OnPanelOpened;
    public event Action OnPanelClosed;

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
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnCraftList += HandleCraftList;
            nm.OnCraftResult += HandleCraftResult;
            nm.OnCookResult += HandleCookResult;
            nm.OnEnchantResultResp += HandleEnchantResult;
        }
    }

    private void OnDestroy()
    {
        var nm = Network.NetworkManager.Instance;
        if (nm != null)
        {
            nm.OnCraftList -= HandleCraftList;
            nm.OnCraftResult -= HandleCraftResult;
            nm.OnCookResult -= HandleCookResult;
            nm.OnEnchantResultResp -= HandleEnchantResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleCraftList(Network.CraftRecipeInfo[] recipes)
    {
        _recipes.Clear();
        _recipes.AddRange(recipes);
        OnRecipeListChanged?.Invoke();
    }

    private void HandleCraftResult(Network.CraftResultData data)
    {
        OnCraftComplete?.Invoke(data);
    }

    private void HandleCookResult(Network.CookResultData data)
    {
        OnCookComplete?.Invoke(data);
    }

    private void HandleEnchantResult(Network.EnchantResultData data)
    {
        OnEnchantComplete?.Invoke(data);
    }

    // ━━━ 공개 API ━━━

    public void OpenPanel()
    {
        _isPanelOpen = true;
        Network.NetworkManager.Instance?.RequestCraftList();
        OnPanelOpened?.Invoke();
    }

    public void ClosePanel()
    {
        _isPanelOpen = false;
        OnPanelClosed?.Invoke();
    }

    public void Craft(string recipeId)
    {
        Network.NetworkManager.Instance?.ExecuteCraft(recipeId);
    }

    public void Cook(string recipeId)
    {
        Network.NetworkManager.Instance?.ExecuteCook(recipeId);
    }

    public void Enchant(byte slot, byte element, byte level)
    {
        Network.NetworkManager.Instance?.RequestEnchant(slot, element, level);
    }

    public void RefreshRecipes(byte category = 0xFF)
    {
        Network.NetworkManager.Instance?.RequestCraftList(category);
    }

    public Network.CraftRecipeInfo GetRecipe(string recipeId)
    {
        for (int i = 0; i < _recipes.Count; i++)
        {
            if (_recipes[i].RecipeId == recipeId)
                return _recipes[i];
        }
        return null;
    }
}
