// ch19/linked_list.cpp: reverse a list, merge two sorted lists, detect a cycle.
#include <cstdio>

struct Node {
    int value;
    Node* next;
};

/// Reverses the list in place and returns the new head.
Node* reverse(Node* head) {
    Node* reversed = nullptr;

    while (head != nullptr) {
        Node* rest = head->next;

        head->next = reversed;
        reversed = head;
        head = rest;
    }

    return reversed;
}

/// Merges two ascending lists into one ascending list, reusing the nodes.
Node* merge_sorted(Node* left, Node* right) {
    Node anchor{0, nullptr};
    Node* tail = &anchor;

    while (left != nullptr && right != nullptr) {
        Node*& smaller = (left->value <= right->value) ? left : right;

        tail->next = smaller;
        tail = smaller;
        smaller = smaller->next;
    }

    tail->next = (left != nullptr) ? left : right;
    return anchor.next;
}

/// Floyd's algorithm: a fast pointer catches a slow one only if the list loops.
bool has_cycle(const Node* head) {
    const Node* slow = head;
    const Node* fast = head;

    while (fast != nullptr && fast->next != nullptr) {
        slow = slow->next;
        fast = fast->next->next;

        if (slow == fast) return true;
    }

    return false;
}

void print_list(const char* label, const Node* head) {
    printf("%s", label);

    for (; head != nullptr; head = head->next) printf(" %d", head->value);

    printf("\n");
}

int main() {
    Node five{5, nullptr}, three{3, &five}, one{1, &three};
    Node six{6, nullptr}, four{4, &six}, two{2, &four};

    Node* merged = merge_sorted(&one, &two);
    print_list("merged  :", merged);

    Node* reversed = reverse(merged);
    print_list("reversed:", reversed);

    printf("cycle before: %s\n", has_cycle(reversed) ? "yes" : "no");

    one.next = &six;   // the last node now points back to the first
    printf("cycle after : %s\n", has_cycle(reversed) ? "yes" : "no");
}
