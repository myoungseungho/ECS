// ━━━ EnvironmentSetup.cs ━━━
// Menu: "ECS Game > Setup Environment"
// 프로시저럴 터레인, 물, 마을 건물, 필드 환경 자동 생성
// art_style.yaml 기반 색상 팔레트

using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class EnvironmentSetup
{
    // ━━━ 터레인 설정 ━━━
    private const int TerrainSize = 200;
    private const int TerrainHeight = 30;
    private const int HeightmapRes = 513;

    // ━━━ art_style.yaml 색상 ━━━
    private static readonly Color GrassColor = HexColor("#408E24");
    private static readonly Color DirtColor = HexColor("#8C5A2E");
    private static readonly Color StoneColor = HexColor("#737373");
    private static readonly Color SandColor = HexColor("#D9C78E");

    // wind_village 팔레트
    private static readonly Color VillageWood = HexColor("#8D6E63");
    private static readonly Color VillageGreen = HexColor("#A5D6A7");
    private static readonly Color VillageGold = HexColor("#FFD54F");

    // 물 색상
    private static readonly Color WaterColor = new Color(0.16f, 0.71f, 0.96f, 0.5f); // #29B6F680

    private const string URPLitShader = "Universal Render Pipeline/Lit";

    [MenuItem("ECS Game/Setup Environment", priority = 5)]
    public static void SetupEnvironment()
    {
        Debug.Log("━━━ [EnvironmentSetup] 환경 생성 시작 ━━━");

        var scene = EditorSceneManager.GetActiveScene();
        if (!scene.isLoaded)
        {
            Debug.LogError("[EnvironmentSetup] 활성 씬이 없습니다.");
            return;
        }

        // 기존 환경 오브젝트 정리
        CleanupExisting(scene);

        CreateTerrain();
        CreateWater();
        CreateVillageBuildings();
        CreateFieldEnvironment();

        EditorSceneManager.MarkSceneDirty(scene);
        Debug.Log("━━━ [EnvironmentSetup] 환경 생성 완료 ━━━");
    }

    /// <summary>
    /// ProjectSetup.CreateGameScene()에서 호출할 수 있는 진입점
    /// </summary>
    public static void SetupEnvironmentInScene()
    {
        CreateTerrain();
        CreateWater();
        CreateVillageBuildings();
        CreateFieldEnvironment();
        Debug.Log("  [Environment] 터레인 + 물 + 마을 + 필드 생성 완료");
    }

    private static void CleanupExisting(UnityEngine.SceneManagement.Scene scene)
    {
        foreach (var root in scene.GetRootGameObjects())
        {
            if (root.name == "Terrain" || root.name == "Water" ||
                root.name == "Village" || root.name == "FieldEnvironment")
            {
                Object.DestroyImmediate(root);
            }
        }
    }

    // ━━━ 1. 프로시저럴 터레인 ━━━

    private static void CreateTerrain()
    {
        var terrainData = new TerrainData();
        terrainData.heightmapResolution = HeightmapRes;
        terrainData.size = new Vector3(TerrainSize, TerrainHeight, TerrainSize);

        // Perlin noise 하이트맵 생성
        float[,] heights = new float[HeightmapRes, HeightmapRes];
        float centerX = HeightmapRes * 0.35f;  // 마을 중앙 (서쪽)
        float centerZ = HeightmapRes * 0.5f;

        for (int z = 0; z < HeightmapRes; z++)
        {
            for (int x = 0; x < HeightmapRes; x++)
            {
                float nx = (float)x / HeightmapRes;
                float nz = (float)z / HeightmapRes;

                // 기본 Perlin 노이즈
                float h = Mathf.PerlinNoise(nx * 3f, nz * 3f) * 0.15f;
                h += Mathf.PerlinNoise(nx * 7f + 100f, nz * 7f + 100f) * 0.05f;

                // 마을 영역 (중앙-서쪽): 평탄하게
                float distFromVillage = Vector2.Distance(
                    new Vector2(x, z), new Vector2(centerX, centerZ)) / HeightmapRes;
                if (distFromVillage < 0.15f)
                {
                    float flatFactor = 1f - (distFromVillage / 0.15f);
                    h = Mathf.Lerp(h, 0.05f, flatFactor * flatFactor);
                }

                // 동/북: 구릉지 (진폭 증가)
                if (nx > 0.5f)
                    h += Mathf.PerlinNoise(nx * 5f + 50f, nz * 5f + 50f) * 0.15f * (nx - 0.5f) * 2f;

                // 북쪽 능선: 산맥
                if (nz > 0.7f)
                {
                    float mountainFactor = (nz - 0.7f) / 0.3f;
                    h += Mathf.PerlinNoise(nx * 4f + 200f, nz * 4f + 200f) * 0.5f * mountainFactor;
                    h += Mathf.PerlinNoise(nx * 8f + 300f, nz * 8f + 300f) * 0.3f * mountainFactor;
                }

                heights[z, x] = Mathf.Clamp01(h);
            }
        }

        terrainData.SetHeights(0, 0, heights);

        // 터레인 레이어 생성
        CreateTerrainLayers(terrainData);

        // 스플랫맵 페인팅
        PaintSplatmap(terrainData, heights);

        // 터레인 오브젝트 생성
        var terrainGo = Terrain.CreateTerrainGameObject(terrainData);
        terrainGo.name = "Terrain";
        terrainGo.transform.position = new Vector3(-50f, 0f, -50f);

        // 에셋으로 저장
        EnsureDirectory("Assets/Terrain");
        AssetDatabase.CreateAsset(terrainData, "Assets/Terrain/MainTerrain.asset");

        Debug.Log("  [Terrain] 200x200 프로시저럴 터레인 생성");
    }

    private static void CreateTerrainLayers(TerrainData terrainData)
    {
        var layers = new TerrainLayer[4];

        // Grass 레이어
        layers[0] = CreateTerrainLayer("Grass", GrassColor);
        // Dirt 레이어
        layers[1] = CreateTerrainLayer("Dirt", DirtColor);
        // Stone 레이어
        layers[2] = CreateTerrainLayer("Stone", StoneColor);
        // Sand 레이어
        layers[3] = CreateTerrainLayer("Sand", SandColor);

        terrainData.terrainLayers = layers;
    }

    private static TerrainLayer CreateTerrainLayer(string name, Color color)
    {
        EnsureDirectory("Assets/Terrain");
        string layerPath = $"Assets/Terrain/Layer_{name}.terrainlayer";

        var existing = AssetDatabase.LoadAssetAtPath<TerrainLayer>(layerPath);
        if (existing != null) return existing;

        var layer = new TerrainLayer();
        layer.tileSize = new Vector2(10, 10);

        // 프로시저럴 텍스처 생성 (단색)
        var tex = new Texture2D(4, 4);
        var pixels = new Color[16];
        for (int i = 0; i < 16; i++) pixels[i] = color;
        tex.SetPixels(pixels);
        tex.Apply();

        string texPath = $"Assets/Terrain/Tex_{name}.asset";
        AssetDatabase.CreateAsset(tex, texPath);
        layer.diffuseTexture = tex;

        AssetDatabase.CreateAsset(layer, layerPath);
        return layer;
    }

    private static void PaintSplatmap(TerrainData terrainData, float[,] heights)
    {
        int alphaRes = terrainData.alphamapResolution;
        float[,,] alphaMaps = new float[alphaRes, alphaRes, 4];
        float centerNx = 0.35f;
        float centerNz = 0.5f;

        for (int z = 0; z < alphaRes; z++)
        {
            for (int x = 0; x < alphaRes; x++)
            {
                float nx = (float)x / alphaRes;
                float nz = (float)z / alphaRes;

                // 높이 샘플링
                int hx = Mathf.Clamp((int)(nx * (HeightmapRes - 1)), 0, HeightmapRes - 1);
                int hz = Mathf.Clamp((int)(nz * (HeightmapRes - 1)), 0, HeightmapRes - 1);
                float h = heights[hz, hx];

                // 경사 계산 (근사치)
                float slope = 0f;
                if (hx > 0 && hx < HeightmapRes - 1 && hz > 0 && hz < HeightmapRes - 1)
                {
                    float dx = heights[hz, hx + 1] - heights[hz, hx - 1];
                    float dz = heights[hz + 1, hx] - heights[hz - 1, hx];
                    slope = Mathf.Sqrt(dx * dx + dz * dz) * HeightmapRes;
                }

                float grass = 0f, dirt = 0f, stone = 0f, sand = 0f;

                // 마을 영역: 흙 + 돌
                float distFromVillage = Vector2.Distance(
                    new Vector2(nx, nz), new Vector2(centerNx, centerNz));
                if (distFromVillage < 0.15f)
                {
                    dirt = 0.6f;
                    stone = 0.4f;
                }
                // 경사면: 돌
                else if (slope > 0.3f)
                {
                    stone = Mathf.Clamp01(slope / 0.5f);
                    grass = 1f - stone;
                }
                // 높은 곳: 돌
                else if (h > 0.4f)
                {
                    stone = (h - 0.4f) / 0.3f;
                    grass = 1f - stone;
                }
                // 물가: 모래
                else if (h < 0.06f)
                {
                    sand = 1f - (h / 0.06f);
                    grass = 1f - sand;
                }
                // 필드: 풀 + 흙
                else
                {
                    grass = 0.7f;
                    dirt = 0.3f;
                }

                // 정규화
                float total = grass + dirt + stone + sand;
                if (total > 0f)
                {
                    alphaMaps[z, x, 0] = grass / total;
                    alphaMaps[z, x, 1] = dirt / total;
                    alphaMaps[z, x, 2] = stone / total;
                    alphaMaps[z, x, 3] = sand / total;
                }
                else
                {
                    alphaMaps[z, x, 0] = 1f;
                }
            }
        }

        terrainData.SetAlphamaps(0, 0, alphaMaps);
    }

    // ━━━ 2. 물 ━━━

    private static void CreateWater()
    {
        var waterGo = GameObject.CreatePrimitive(PrimitiveType.Plane);
        waterGo.name = "Water";
        waterGo.transform.position = new Vector3(50f, 1.0f, 50f);
        waterGo.transform.localScale = new Vector3(8f, 1f, 8f);

        var renderer = waterGo.GetComponent<MeshRenderer>();
        if (renderer != null)
        {
            var shader = Shader.Find(URPLitShader) ?? Shader.Find("Standard");
            var mat = new Material(shader);
            mat.SetColor("_BaseColor", WaterColor);

            // 투명 설정
            mat.SetFloat("_Surface", 1); // Transparent
            mat.SetFloat("_Blend", 0);   // Alpha
            mat.SetOverrideTag("RenderType", "Transparent");
            mat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            mat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            mat.SetInt("_ZWrite", 0);
            mat.renderQueue = 3000;

            renderer.sharedMaterial = mat;
        }

        // 콜라이더 제거 (캐릭터가 물 위를 걸을 수 있도록)
        var col = waterGo.GetComponent<Collider>();
        if (col != null) Object.DestroyImmediate(col);

        Debug.Log("  [Water] 반투명 수면 생성");
    }

    // ━━━ 3. 마을 건물 ━━━

    private static void CreateVillageBuildings()
    {
        var villageParent = new GameObject("Village");
        villageParent.transform.position = new Vector3(20f, 0f, 50f);

        var shader = Shader.Find(URPLitShader) ?? Shader.Find("Standard");

        // 건물 배치 데이터: (위치, 크기, 색상, 이름)
        CreateBuilding(villageParent.transform, "House_1", new Vector3(0, 2, 0), new Vector3(4, 4, 5), VillageWood, shader);
        CreateRoof(villageParent.transform, "Roof_1", new Vector3(0, 4.5f, 0), new Vector3(5, 1.5f, 6), VillageGold, shader);

        CreateBuilding(villageParent.transform, "House_2", new Vector3(10, 1.5f, 3), new Vector3(3, 3, 4), VillageWood, shader);
        CreateRoof(villageParent.transform, "Roof_2", new Vector3(10, 3.5f, 3), new Vector3(4, 1.2f, 5), VillageGold, shader);

        CreateBuilding(villageParent.transform, "House_3", new Vector3(-8, 2.5f, -5), new Vector3(5, 5, 6), VillageWood, shader);
        CreateRoof(villageParent.transform, "Roof_3", new Vector3(-8, 5.5f, -5), new Vector3(6, 1.5f, 7), VillageGold, shader);

        CreateBuilding(villageParent.transform, "Shop_1", new Vector3(5, 1, 10), new Vector3(3, 2, 3), VillageWood, shader);
        CreateRoof(villageParent.transform, "ShopRoof_1", new Vector3(5, 2.3f, 10), new Vector3(4, 0.8f, 4), VillageGold, shader);

        CreateBuilding(villageParent.transform, "Shop_2", new Vector3(-3, 1, 10), new Vector3(3, 2, 3), VillageWood, shader);

        // 시장 노점 (테이블)
        CreateBuilding(villageParent.transform, "Market_1", new Vector3(1, 0.5f, 15), new Vector3(4, 1, 2), VillageWood, shader);
        CreateBuilding(villageParent.transform, "Market_2", new Vector3(-5, 0.5f, 15), new Vector3(4, 1, 2), VillageWood, shader);

        // 분수대
        CreateFountain(villageParent.transform, new Vector3(0, 0, 8), shader);

        // 성벽 조각
        CreateBuilding(villageParent.transform, "Wall_1", new Vector3(-15, 2, 0), new Vector3(1.5f, 4, 20), StoneColor, shader);
        CreateBuilding(villageParent.transform, "Wall_2", new Vector3(15, 2, -10), new Vector3(30, 4, 1.5f), StoneColor, shader);

        Debug.Log("  [Village] 마을 건물 15개 생성");
    }

    private static void CreateBuilding(Transform parent, string name, Vector3 pos, Vector3 scale, Color color, Shader shader)
    {
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name;
        go.transform.SetParent(parent, false);
        go.transform.localPosition = pos;
        go.transform.localScale = scale;

        var mat = new Material(shader);
        mat.SetColor("_BaseColor", color);
        go.GetComponent<MeshRenderer>().sharedMaterial = mat;
    }

    private static void CreateRoof(Transform parent, string name, Vector3 pos, Vector3 scale, Color color, Shader shader)
    {
        // 지붕을 기울인 큐브로 표현
        var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
        go.name = name;
        go.transform.SetParent(parent, false);
        go.transform.localPosition = pos;
        go.transform.localScale = scale;
        go.transform.localRotation = Quaternion.Euler(0, 0, 0);

        var mat = new Material(shader);
        mat.SetColor("_BaseColor", color);
        go.GetComponent<MeshRenderer>().sharedMaterial = mat;
    }

    private static void CreateFountain(Transform parent, Vector3 pos, Shader shader)
    {
        var fountain = new GameObject("Fountain");
        fountain.transform.SetParent(parent, false);
        fountain.transform.localPosition = pos;

        // 기반
        var baseGo = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        baseGo.name = "FountainBase";
        baseGo.transform.SetParent(fountain.transform, false);
        baseGo.transform.localPosition = Vector3.zero;
        baseGo.transform.localScale = new Vector3(3f, 0.5f, 3f);
        var baseMat = new Material(shader);
        baseMat.SetColor("_BaseColor", StoneColor);
        baseGo.GetComponent<MeshRenderer>().sharedMaterial = baseMat;

        // 중앙 기둥
        var pillar = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        pillar.name = "FountainPillar";
        pillar.transform.SetParent(fountain.transform, false);
        pillar.transform.localPosition = new Vector3(0, 1f, 0);
        pillar.transform.localScale = new Vector3(0.5f, 1.5f, 0.5f);
        pillar.GetComponent<MeshRenderer>().sharedMaterial = baseMat;

        // 물
        var water = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        water.name = "FountainWater";
        water.transform.SetParent(fountain.transform, false);
        water.transform.localPosition = new Vector3(0, 0.4f, 0);
        water.transform.localScale = new Vector3(2.5f, 0.1f, 2.5f);
        var waterMat = new Material(shader);
        waterMat.SetColor("_BaseColor", WaterColor);
        water.GetComponent<MeshRenderer>().sharedMaterial = waterMat;
        var waterCol = water.GetComponent<Collider>();
        if (waterCol != null) Object.DestroyImmediate(waterCol);
    }

    // ━━━ 4. 필드 환경 ━━━

    private static void CreateFieldEnvironment()
    {
        var fieldParent = new GameObject("FieldEnvironment");
        var shader = Shader.Find(URPLitShader) ?? Shader.Find("Standard");

        // 나무 50개
        var treeTrunkMat = new Material(shader);
        treeTrunkMat.SetColor("_BaseColor", VillageWood);
        var treeLeafMat = new Material(shader);
        treeLeafMat.SetColor("_BaseColor", VillageGreen);

        var rand = new System.Random(42);
        for (int i = 0; i < 50; i++)
        {
            float x = (float)(rand.NextDouble() * 140 - 20);
            float z = (float)(rand.NextDouble() * 140 - 20);

            // 마을 영역 회피
            if (x > 5 && x < 35 && z > 35 && z < 65) continue;

            CreateTree(fieldParent.transform, $"Tree_{i}", new Vector3(x, 0, z),
                treeTrunkMat, treeLeafMat);
        }

        // 바위 30개
        var rockMat = new Material(shader);
        rockMat.SetColor("_BaseColor", StoneColor);

        for (int i = 0; i < 30; i++)
        {
            float x = (float)(rand.NextDouble() * 140 - 20);
            float z = (float)(rand.NextDouble() * 140 - 20);

            var rock = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            rock.name = $"Rock_{i}";
            rock.transform.SetParent(fieldParent.transform, false);
            float scale = 0.5f + (float)rand.NextDouble() * 1.5f;
            rock.transform.localPosition = new Vector3(x, scale * 0.3f, z);
            rock.transform.localScale = new Vector3(scale, scale * 0.6f, scale);
            rock.transform.localRotation = Quaternion.Euler(
                (float)rand.NextDouble() * 20f,
                (float)rand.NextDouble() * 360f,
                (float)rand.NextDouble() * 20f);
            rock.GetComponent<MeshRenderer>().sharedMaterial = rockMat;
        }

        // 횃불 포인트라이트 10개
        for (int i = 0; i < 10; i++)
        {
            float x = (float)(rand.NextDouble() * 100);
            float z = (float)(rand.NextDouble() * 100);

            var torchGo = new GameObject($"Torch_{i}");
            torchGo.transform.SetParent(fieldParent.transform, false);
            torchGo.transform.localPosition = new Vector3(x, 2f, z);

            var torchLight = torchGo.AddComponent<Light>();
            torchLight.type = LightType.Point;
            torchLight.color = new Color(1f, 0.7f, 0.3f);
            torchLight.intensity = 2f;
            torchLight.range = 8f;
            torchLight.shadows = LightShadows.None;

            // 횃불 기둥
            var pole = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            pole.name = "TorchPole";
            pole.transform.SetParent(torchGo.transform, false);
            pole.transform.localPosition = new Vector3(0, -1f, 0);
            pole.transform.localScale = new Vector3(0.1f, 1f, 0.1f);
            pole.GetComponent<MeshRenderer>().sharedMaterial = treeTrunkMat;
        }

        Debug.Log("  [Field] 나무 50 + 바위 30 + 횃불 10 생성");
    }

    private static void CreateTree(Transform parent, string name, Vector3 pos,
        Material trunkMat, Material leafMat)
    {
        var tree = new GameObject(name);
        tree.transform.SetParent(parent, false);
        tree.transform.localPosition = pos;

        // 줄기 (실린더)
        var trunk = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        trunk.name = "Trunk";
        trunk.transform.SetParent(tree.transform, false);
        trunk.transform.localPosition = new Vector3(0, 1.5f, 0);
        trunk.transform.localScale = new Vector3(0.3f, 1.5f, 0.3f);
        trunk.GetComponent<MeshRenderer>().sharedMaterial = trunkMat;

        // 나뭇잎 (구체)
        var leaves = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        leaves.name = "Leaves";
        leaves.transform.SetParent(tree.transform, false);
        leaves.transform.localPosition = new Vector3(0, 4f, 0);
        leaves.transform.localScale = new Vector3(2.5f, 2.5f, 2.5f);
        leaves.GetComponent<MeshRenderer>().sharedMaterial = leafMat;

        // 나뭇잎 콜라이더 제거 (성능)
        var leavesCol = leaves.GetComponent<Collider>();
        if (leavesCol != null) Object.DestroyImmediate(leavesCol);
    }

    // ━━━ 유틸 ━━━

    private static Color HexColor(string hex)
    {
        if (ColorUtility.TryParseHtmlString(hex, out var color))
            return color;
        return Color.magenta;
    }

    private static void EnsureDirectory(string path)
    {
        if (!AssetDatabase.IsValidFolder(path))
        {
            string parent = System.IO.Path.GetDirectoryName(path).Replace("\\", "/");
            string folder = System.IO.Path.GetFileName(path);
            AssetDatabase.CreateFolder(parent, folder);
        }
    }
}
