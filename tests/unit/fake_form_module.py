calls = 0


def make_form(services=None):
    global calls
    calls += 1
    return services or "form-created"
