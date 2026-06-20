
#include <Arduino.h>

#include <sstream>
#include <vector>

#include "semver.h"

using namespace std;

vector<string> split(const string &s, char delim) {
    vector<string> result;
    stringstream ss(s);
    string item;

    while (getline(ss, item, delim)) {
        result.push_back(item);
    }

    return result;
}

semver_t from_string(const string &version) {
    if (version.empty()) {
        return {0, 0, 0, nullptr, nullptr};
    }
    auto numbers = split(version, '.');
    // Tolerate version strings with fewer than three dotted segments (e.g. a
    // remote release tag of "v2" or "v1.2"): missing minor/patch default to 0.
    // Without this, numbers.at(1)/.at(2) throws std::out_of_range and aborts the
    // device when checkForUpdates() parses a malformed upstream tag.
    auto major = numbers.size() > 0 ? atoi(numbers.at(0).c_str()) : 0;
    auto minor = numbers.size() > 1 ? atoi(numbers.at(1).c_str()) : 0;
    int patch = 0;
    char *prerelease_ptr = nullptr;

    if (numbers.size() > 2) {
        auto split_at = numbers.at(2).find('-');
        if (split_at != string::npos) {
            patch = atoi(numbers.at(2).substr(0, split_at).c_str());
            auto prerelease = numbers.at(2).substr(split_at + 1);
            prerelease_ptr = (char *)malloc(prerelease.length() + 1);
            if (prerelease_ptr != nullptr) {
                prerelease.copy(prerelease_ptr, prerelease.length());
                prerelease_ptr[prerelease.length()] = '\0';
            }
        } else {
            patch = atoi(numbers.at(2).c_str());
        }
    }

    semver_t _ver = {major, minor, patch, nullptr, prerelease_ptr};

    return _ver;
}

String render_to_string(const semver_t &version) {
    String rendered = String(version.major) + "." + String(version.minor) + "." + String(version.patch);
    if (version.prerelease != nullptr) {
        rendered += "-" + String(version.prerelease);
    }
    return rendered;
}

bool operator>(const semver_t &x, const semver_t &y) { return semver_compare(x, y) > 0; }
