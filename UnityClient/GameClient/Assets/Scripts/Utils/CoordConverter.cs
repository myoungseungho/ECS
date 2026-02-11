using UnityEngine;

public static class CoordConverter
{
    // 서버 좌표 (0~1000, 2D) -> Unity 좌표 (3D)
    // 서버 1000x1000 -> Unity 100x100 유닛
    public static Vector3 ServerToUnity(float sx, float sy)
    {
        return new Vector3(sx * 0.1f, 0f, sy * 0.1f);
    }

    // Unity -> 서버
    public static (float x, float y) UnityToServer(Vector3 pos)
    {
        return (pos.x * 10f, pos.z * 10f);
    }
}
