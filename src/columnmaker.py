# Make beautiful columns, originally implemeted by rce

def columnmaker(titles,data):

    def column_width(rows, index):
        """Returns the width of the widest value in column"""
        return max([len(str(row[index])) for row in rows])

    def format_row(row, column_widths):
        """Formats a single row"""
        width_adjusted = [ str(data).ljust(width) for data, width in zip(row, column_widths) ]
        return " | ".join(width_adjusted)

    def format_table(rows):
        """Formats table"""
        if not rows or len(rows) < 1:
            raise ValueError("Table should have at least one row")

        column_count = len(rows[0])
        if not all([ len(row) == column_count for row in rows ]):
            raise ValueError("All rows should have same amount of columns")

        column_widths = [ column_width(rows, index) for index in range(0, column_count) ]
        formatted_row = [ format_row(row, column_widths) for row in rows ]

        return "\n".join(formatted_row)

    table = format_table([(titles),*data])
    return table
