def calculate_average(numbers):
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)


def test_calculate_average():
    result = calculate_average([10, 20, 30])
    assert result == 20

    result = calculate_average([])
    assert result == 0