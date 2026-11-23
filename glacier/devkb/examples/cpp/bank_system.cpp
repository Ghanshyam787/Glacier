/* NAME: bank_system
   DESC: OOP bank: abstract Account, Savings/Current subclasses, virtual functions, exceptions, std::map storage, transfer.
   KEYWORDS: bank, oop, class, inheritance, polymorphism, virtual, abstract, exception, map, unique_ptr, account, project */
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>

class InsufficientFunds : public std::runtime_error {
public:
    explicit InsufficientFunds(const std::string& m) : std::runtime_error(m) {}
};

class Account {
public:
    Account(std::string id, std::string owner, double opening)
        : id_(std::move(id)), owner_(std::move(owner)), balance_(opening) {}
    virtual ~Account() = default;
    void deposit(double amt) {
        if (amt <= 0) throw std::invalid_argument("deposit must be positive");
        balance_ += amt;
    }
    virtual void withdraw(double amt) {
        if (amt <= 0) throw std::invalid_argument("withdrawal must be positive");
        if (amt > available()) throw InsufficientFunds("insufficient funds in " + id_);
        balance_ -= amt;
    }
    virtual double available() const { return balance_; }
    virtual std::string type() const = 0;
    const std::string& id() const { return id_; }
    const std::string& owner() const { return owner_; }
    double balance() const { return balance_; }
protected:
    std::string id_, owner_;
    double balance_;
};

class Savings : public Account {
public:
    using Account::Account;
    std::string type() const override { return "Savings"; }
    void add_interest(double rate) { balance_ += balance_ * rate; }
};

class Current : public Account {
public:
    Current(std::string id, std::string owner, double opening, double overdraft)
        : Account(std::move(id), std::move(owner), opening), overdraft_(overdraft) {}
    std::string type() const override { return "Current"; }
    double available() const override { return balance_ + overdraft_; }
private:
    double overdraft_;
};

class Bank {
public:
    Account& open(std::unique_ptr<Account> acc) {
        auto id = acc->id();
        auto [it, ok] = accounts_.emplace(id, std::move(acc));
        if (!ok) throw std::invalid_argument("duplicate account id " + id);
        return *it->second;
    }
    Account& get(const std::string& id) {
        auto it = accounts_.find(id);
        if (it == accounts_.end()) throw std::out_of_range("no such account " + id);
        return *it->second;
    }
    void transfer(const std::string& from, const std::string& to, double amt) {
        Account& a = get(from);
        Account& b = get(to);
        a.withdraw(amt);
        b.deposit(amt);
    }
    void report() const {
        std::cout << std::fixed << std::setprecision(2);
        for (const auto& [id, acc] : accounts_)
            std::cout << std::left << std::setw(6) << id << std::setw(10) << acc->type()
                      << std::setw(10) << acc->owner() << std::right << std::setw(10) << acc->balance() << '\n';
    }
private:
    std::map<std::string, std::unique_ptr<Account>> accounts_;
};

int main() {
    Bank bank;
    bank.open(std::make_unique<Savings>("S1", "Asha", 1000));
    bank.open(std::make_unique<Current>("C1", "Ravi", 200, 500));
    try {
        bank.transfer("S1", "C1", 300);
        bank.get("C1").withdraw(900);
        bank.get("C1").withdraw(500);
    } catch (const InsufficientFunds& e) {
        std::cout << "Error: " << e.what() << '\n';
    } catch (const std::exception& e) {
        std::cout << "Problem: " << e.what() << '\n';
    }
    if (auto* s = dynamic_cast<Savings*>(&bank.get("S1"))) s->add_interest(0.04);
    bank.report();
}
