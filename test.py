data = [
        {'name':'Denis Korir','amount':500},
        {'name':'James Mwaniki','amount':500},
        {'name':'Peter Kimani','amount':500},
        {'name':'Peru Senray','amount':500}
        ]

print(type(data))
for line in data:
    print(line['name'] + '::' + str(line['amount']))
