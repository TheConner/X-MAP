# -*- coding: utf-8 -*-
"""A class to clean the dataset."""
import re
from datetime import datetime


class BaselinerClean:
    def __init__(
            self, num_atleast_rating, size_subset,
            date_from, date_to, domain_label):
        """initialize  parameter.
        Args:
            num_atleast_rating:
                For each user, it rated at least 'num_atleast_rating' items.
            size_subset:
                The number of observation we want to choose.
            date_from:
                The starting date of ratings.
            date_to:
                The end date of ratings.
            domain_label:
                Add a domain label to the original dataset.
        """
        self.num_atleast_rating = num_atleast_rating
        self.size_subset = size_subset
        self.period = range(date_from, date_to + 1)
        self.label = domain_label

    def parse_time(self, s):
        """convert unix timestamp to readable date.
        Args:
            s: unix timestamp (string)
        Returns:
            datetime
        """
        return datetime.fromtimestamp(float(s))

    def parse_line(self, iterators):
        """parse a line.
        Args:
            iterators: data in lines with format: 'uid, iid, rating, datetime'.
        Returns:
            (uid, [iid + domain_label, rating, datetime])
        """
        record = {}
        for line in iterators:
            line = line.strip()
            colonPos = line.find(':')
            # If end of JSON record is reached
            if colonPos == -1:
                # At this point we should have a complete record
                # Check if record has required fields
                if ("review/time" in record 
                    and "product/productId" in record
                    and "review/score" in record
                    and "review/userId" in record):
                    time = self.parse_time(record["review/time"])

                    # Now, the line needs to be in the period of time we care about
                    if (time.year in self.period):
                        yield(
                            # UID
                            record["review/userId"],
                                # [iid + domain_label, rating, datetime]
                                (
                                    record["product/productId"] + self.label,
                                    float(review["review/score"]),
                                    time
                                ))
                    record = {}
                    continue
                else:
                    # Record does not have required data
                    record = {}
                    continue
            


    def parse_data(self, originalRDD):
        """parse the dataset."""
        return originalRDD.mapPartitions(self.parse_line)

    def take_partial_data(self, dataRDD):
        """take partial data to do the computation."""
        return dataRDD.take(self.size_subset)

    def remove_invalid(self, iterators):
        """remove invalid rating, e.g., old or duplicate.
        iterators is a set of line in the form of [uid, (iid, rating, time)*].
        """
        def check_invalid(line, tmpdict):
            """check data and update invalid data.
            e.g., we only use latest data.
            """
            iid, rating, time = line
            if time > tmpdict[iid][2]:
                tmpdict[iid] = line
            return tmpdict

        for uid, ratings in iterators:
            tmpdict = {}
            for token in ratings:
                # token: in the form of (iid, rating, time)
                if token[0] in tmpdict.keys():
                    tmpdict = check_invalid(token, tmpdict)
                else:
                    tmpdict[token[0]] = token
            yield uid, list(tmpdict.values())

    def filter_data(self, dataRDD):
        """filter the invalid data.
        e.g., 1. duplicate data; 2. same uid, iid, but with different rating.
        """
        seq_op = (lambda a, b: a + [b])
        comb_op = (lambda a, b: a + b)
        groupedRDD = dataRDD.aggregateByKey([], seq_op, comb_op)
        return groupedRDD.mapPartitions(self.remove_invalid)

    def clean_data(self, filteredRDD):
        """remove users who have low rating frequency."""
        return filteredRDD.filter(
            lambda line: len(line[1]) >= self.num_atleast_rating)
