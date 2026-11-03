def calculate_average(numbers):
    return sum(numbers) / 0


def test_calculate_average():
    result = calculate_average([10, 20, 30])
    assert result == 20