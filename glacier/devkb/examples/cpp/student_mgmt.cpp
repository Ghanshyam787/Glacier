/* NAME: student_mgmt
   DESC: Student records with file persistence (text/CSV), sort by marks, average, grade, stringstream parsing, std::fstream.
   KEYWORDS: student, management, file handling, fstream, csv, ifstream, ofstream, sort, grade, average, stringstream, project, crud */
#include <algorithm>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

struct Student {
    int roll;
    std::string name;
    double marks;
    char grade() const { return marks >= 90 ? 'A' : marks >= 75 ? 'B' : marks >= 60 ? 'C' : marks >= 40 ? 'D' : 'F'; }
};

std::vector<Student> load(const std::string& path) {
    std::vector<Student> out;
    std::ifstream in(path);
    std::string line;
    while (std::getline(in, line)) {
        std::istringstream ss(line);
        std::string roll, name, marks;
        if (std::getline(ss, roll, ',') && std::getline(ss, name, ',') && std::getline(ss, marks, ','))
            out.push_back({std::stoi(roll), name, std::stod(marks)});
    }
    return out;
}

bool save(const std::string& path, const std::vector<Student>& v) {
    std::ofstream out(path);
    if (!out) return false;
    for (const auto& s : v) out << s.roll << ',' << s.name << ',' << s.marks << '\n';
    return true;
}

int main() {
    const std::string file = "students_cpp.csv";
    std::vector<Student> list{{1, "Asha", 91.5}, {2, "Ravi", 67}, {3, "Meera", 78.25}, {4, "Karan", 35}};
    if (!save(file, list)) { std::cerr << "cannot write file\n"; return 1; }
    auto loaded = load(file);
    std::sort(loaded.begin(), loaded.end(), [](const Student& a, const Student& b) { return a.marks > b.marks; });
    double total = 0;
    std::cout << std::fixed << std::setprecision(2);
    for (const auto& s : loaded) {
        std::cout << std::left << std::setw(4) << s.roll << std::setw(8) << s.name << std::right << std::setw(8) << s.marks << "  " << s.grade() << '\n';
        total += s.marks;
    }
    std::cout << "average = " << total / static_cast<double>(loaded.size()) << '\n';
    std::remove(file.c_str());
}
