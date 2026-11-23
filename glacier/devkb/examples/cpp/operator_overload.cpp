/* NAME: operator_overload
   DESC: Operator overloading: Vector2D and Fraction classes with +,-,*,/, ==, <, <<, >>, unary minus, spaceship-free, friend functions.
   KEYWORDS: operator overloading, operator, friend, fraction, vector, complex number, ostream, istream, const correctness, gcd, class */
#include <iostream>
#include <numeric>
#include <stdexcept>

class Fraction {
public:
    Fraction(long n = 0, long d = 1) : num_(n), den_(d) {
        if (d == 0) throw std::invalid_argument("zero denominator");
        normalize();
    }
    Fraction operator+(const Fraction& o) const { return {num_ * o.den_ + o.num_ * den_, den_ * o.den_}; }
    Fraction operator-(const Fraction& o) const { return {num_ * o.den_ - o.num_ * den_, den_ * o.den_}; }
    Fraction operator*(const Fraction& o) const { return {num_ * o.num_, den_ * o.den_}; }
    Fraction operator/(const Fraction& o) const {
        if (o.num_ == 0) throw std::domain_error("divide by zero fraction");
        return {num_ * o.den_, den_ * o.num_};
    }
    Fraction operator-() const { return {-num_, den_}; }
    bool operator==(const Fraction& o) const { return num_ == o.num_ && den_ == o.den_; }
    bool operator<(const Fraction& o) const { return num_ * o.den_ < o.num_ * den_; }
    friend std::ostream& operator<<(std::ostream& os, const Fraction& f) {
        return f.den_ == 1 ? os << f.num_ : os << f.num_ << '/' << f.den_;
    }
private:
    void normalize() {
        if (den_ < 0) { num_ = -num_; den_ = -den_; }
        long g = std::gcd(num_ < 0 ? -num_ : num_, den_);
        if (g > 1) { num_ /= g; den_ /= g; }
    }
    long num_, den_;
};

struct Vec2 {
    double x = 0, y = 0;
    Vec2 operator+(Vec2 o) const { return {x + o.x, y + o.y}; }
    Vec2 operator-(Vec2 o) const { return {x - o.x, y - o.y}; }
    Vec2 operator*(double k) const { return {x * k, y * k}; }
    double dot(Vec2 o) const { return x * o.x + y * o.y; }
    Vec2& operator+=(Vec2 o) { x += o.x; y += o.y; return *this; }
};
inline Vec2 operator*(double k, Vec2 v) { return v * k; }
inline std::ostream& operator<<(std::ostream& os, Vec2 v) { return os << '(' << v.x << ", " << v.y << ')'; }

int main() {
    Fraction a(1, 2), b(3, 4);
    std::cout << a << " + " << b << " = " << a + b << '\n';
    std::cout << a << " * " << b << " = " << a * b << '\n';
    std::cout << a << " / " << b << " = " << a / b << '\n';
    std::cout << std::boolalpha << "a < b: " << (a < b) << ", -a = " << -a << ", 2/4 == 1/2: " << (Fraction(2, 4) == a) << '\n';
    try { a / Fraction(0); } catch (const std::exception& e) { std::cout << "error: " << e.what() << '\n'; }
    Vec2 p{1, 2}, q{3, 4};
    p += q;
    std::cout << "p=" << p << " 2*q=" << 2 * q << " dot=" << p.dot(q) << '\n';
}
