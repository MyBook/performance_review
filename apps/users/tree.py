from apps.users.models import User


def build_tree(user2manager, tree, employee):
    subordinates = [user for user, manager in user2manager.items() if manager == employee]
    tree[employee] = {
        s: {} for s in subordinates
    }
    for subordinate in subordinates:
        build_tree(user2manager, tree[employee], subordinate)
    return tree


def get_people_tree():
    users = User.active.select_related('manager').all().order_by('last_name')
    bosses = []
    user2manager = {}
    for user in users:
        if user.is_boss:
            bosses.append(user)
        user2manager[user] = user.manager

    for boss in bosses:
        tree = dict()
        yield build_tree(user2manager, tree, boss)
