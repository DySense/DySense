
def find_last_index(list_to_search, element):
    try:
        return (len(list_to_search) - 1) - list_to_search[::-1].index(element)
    except ValueError:
        return -1 # element not found at all
    
def pretty(text):
    return text.replace('_',' ').title()