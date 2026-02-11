#pragma once

// ━━━ ConfigLoader: CSV/JSON 기반 데이터 드리븐 설계 ━━━
//
// 목적: 하드코딩 대신 외부 파일에서 게임 데이터 로드
//        코드 수정 없이 밸런스 조정 가능
//
// CSV 포맷:
//   첫 줄 = 헤더 (컬럼명)
//   나머지 = 데이터
//   예: id,name,hp,attack
//       1,Goblin,100,15
//       2,Dragon,5000,200
//
// JSON 포맷:
//   키-값 설정 파일
//   예: {"tick_rate": 30, "max_players": 200}
//
// 사용법:
//   ConfigLoader cfg;
//   cfg.LoadCSV("monsters.csv");
//   auto& row = cfg.GetRow("monsters", 0);
//   int hp = row.GetInt("hp");

#include <string>
#include <vector>
#include <unordered_map>
#include <fstream>
#include <sstream>
#include <cstdio>

// CSV 한 행
class ConfigRow {
public:
    void Set(const std::string& key, const std::string& value) {
        data_[key] = value;
    }

    std::string GetString(const std::string& key, const std::string& def = "") const {
        auto it = data_.find(key);
        return it != data_.end() ? it->second : def;
    }

    int GetInt(const std::string& key, int def = 0) const {
        auto it = data_.find(key);
        if (it == data_.end()) return def;
        try { return std::stoi(it->second); }
        catch (...) { return def; }
    }

    float GetFloat(const std::string& key, float def = 0.0f) const {
        auto it = data_.find(key);
        if (it == data_.end()) return def;
        try { return std::stof(it->second); }
        catch (...) { return def; }
    }

    bool HasKey(const std::string& key) const {
        return data_.count(key) > 0;
    }

    const std::unordered_map<std::string, std::string>& GetAll() const {
        return data_;
    }

private:
    std::unordered_map<std::string, std::string> data_;
};

// CSV 테이블 (이름으로 관리)
class ConfigTable {
public:
    std::vector<std::string> headers;
    std::vector<ConfigRow> rows;

    int GetRowCount() const { return static_cast<int>(rows.size()); }

    const ConfigRow& GetRow(int index) const {
        return rows[index];
    }

    // 특정 컬럼 값으로 행 검색
    const ConfigRow* FindByKey(const std::string& column, const std::string& value) const {
        for (auto& row : rows) {
            if (row.GetString(column) == value) return &row;
        }
        return nullptr;
    }

    // int 키로 검색 (id 컬럼)
    const ConfigRow* FindById(int id) const {
        std::string sid = std::to_string(id);
        return FindByKey("id", sid);
    }
};

class ConfigLoader {
public:
    // CSV 파일 로드
    bool LoadCSV(const std::string& name, const std::string& filepath) {
        std::ifstream file(filepath);
        if (!file.is_open()) {
            printf("[Config] Failed to open: %s\n", filepath.c_str());
            return false;
        }

        ConfigTable table;
        std::string line;

        // 헤더 읽기
        if (!std::getline(file, line)) return false;

        // BOM 제거
        if (line.size() >= 3 &&
            (unsigned char)line[0] == 0xEF &&
            (unsigned char)line[1] == 0xBB &&
            (unsigned char)line[2] == 0xBF) {
            line = line.substr(3);
        }

        // \r 제거
        if (!line.empty() && line.back() == '\r') line.pop_back();

        table.headers = SplitCSV(line);

        // 데이터 읽기
        while (std::getline(file, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.empty()) continue;

            auto values = SplitCSV(line);
            ConfigRow row;
            for (size_t i = 0; i < table.headers.size() && i < values.size(); i++) {
                row.Set(table.headers[i], values[i]);
            }
            table.rows.push_back(std::move(row));
        }

        tables_[name] = std::move(table);
        printf("[Config] Loaded '%s': %d rows from %s\n",
               name.c_str(), GetTable(name)->GetRowCount(), filepath.c_str());
        return true;
    }

    // 메모리에서 직접 CSV 로드 (테스트용)
    bool LoadCSVFromString(const std::string& name, const std::string& csv_data) {
        std::istringstream stream(csv_data);
        ConfigTable table;
        std::string line;

        if (!std::getline(stream, line)) return false;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        table.headers = SplitCSV(line);

        while (std::getline(stream, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.empty()) continue;

            auto values = SplitCSV(line);
            ConfigRow row;
            for (size_t i = 0; i < table.headers.size() && i < values.size(); i++) {
                row.Set(table.headers[i], values[i]);
            }
            table.rows.push_back(std::move(row));
        }

        tables_[name] = std::move(table);
        return true;
    }

    // JSON 키-값 설정 로드 (간단한 flat JSON만 지원)
    bool LoadJSON(const std::string& name, const std::string& filepath) {
        std::ifstream file(filepath);
        if (!file.is_open()) return false;

        std::string content((std::istreambuf_iterator<char>(file)),
                            std::istreambuf_iterator<char>());
        return LoadJSONFromString(name, content);
    }

    // 메모리에서 JSON 로드 (테스트용)
    bool LoadJSONFromString(const std::string& name, const std::string& json_data) {
        ConfigRow settings;

        // 간단한 JSON 파서 (flat key-value만, 중첩 미지원)
        std::string data = json_data;
        // { } 제거
        size_t start = data.find('{');
        size_t end = data.rfind('}');
        if (start == std::string::npos || end == std::string::npos) return false;
        data = data.substr(start + 1, end - start - 1);

        // 키-값 파싱
        size_t pos = 0;
        while (pos < data.size()) {
            // 키 찾기
            size_t q1 = data.find('"', pos);
            if (q1 == std::string::npos) break;
            size_t q2 = data.find('"', q1 + 1);
            if (q2 == std::string::npos) break;
            std::string key = data.substr(q1 + 1, q2 - q1 - 1);

            // : 찾기
            size_t colon = data.find(':', q2 + 1);
            if (colon == std::string::npos) break;

            // 값 찾기
            size_t vstart = colon + 1;
            while (vstart < data.size() && (data[vstart] == ' ' || data[vstart] == '\t'
                   || data[vstart] == '\n' || data[vstart] == '\r')) vstart++;

            std::string value;
            if (vstart < data.size() && data[vstart] == '"') {
                // 문자열 값
                size_t vend = data.find('"', vstart + 1);
                if (vend == std::string::npos) break;
                value = data.substr(vstart + 1, vend - vstart - 1);
                pos = vend + 1;
            } else {
                // 숫자/bool 값
                size_t vend = vstart;
                while (vend < data.size() && data[vend] != ',' && data[vend] != '}'
                       && data[vend] != '\n' && data[vend] != '\r') vend++;
                value = data.substr(vstart, vend - vstart);
                // 공백 제거
                while (!value.empty() && (value.back() == ' ' || value.back() == '\t'))
                    value.pop_back();
                pos = vend;
            }

            settings.Set(key, value);
            // 다음 항목으로
            size_t comma = data.find(',', pos);
            pos = (comma != std::string::npos) ? comma + 1 : data.size();
        }

        json_settings_[name] = std::move(settings);
        return true;
    }

    // 테이블 가져오기
    const ConfigTable* GetTable(const std::string& name) const {
        auto it = tables_.find(name);
        return it != tables_.end() ? &it->second : nullptr;
    }

    // JSON 설정 가져오기
    const ConfigRow* GetSettings(const std::string& name) const {
        auto it = json_settings_.find(name);
        return it != json_settings_.end() ? &it->second : nullptr;
    }

    // 로드된 테이블 수
    int GetTableCount() const { return static_cast<int>(tables_.size()); }
    int GetSettingsCount() const { return static_cast<int>(json_settings_.size()); }

private:
    std::vector<std::string> SplitCSV(const std::string& line) {
        std::vector<std::string> result;
        std::string field;
        bool in_quotes = false;

        for (size_t i = 0; i < line.size(); i++) {
            char c = line[i];
            if (c == '"') {
                in_quotes = !in_quotes;
            } else if (c == ',' && !in_quotes) {
                result.push_back(field);
                field.clear();
            } else {
                field += c;
            }
        }
        result.push_back(field);
        return result;
    }

    std::unordered_map<std::string, ConfigTable> tables_;
    std::unordered_map<std::string, ConfigRow> json_settings_;
};
