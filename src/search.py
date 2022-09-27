from collections import defaultdict


class Search:
    def __init__(self):
        self.tracks = []

    # TODO: this is a database task or function. We should let the database optimise this search.
    def search_tracks(self, tracks, keywords):
        for track in tracks:
            match_counts = track.matches_search_keywords(keywords)
            if match_counts:
                track.match_count = match_counts
                self.tracks.append(track)

    def get_results(self, result_count):
        return sorted(self.tracks, key=lambda x: x.match_count)[:result_count]

    def has_results(self):
        return bool(self.tracks)