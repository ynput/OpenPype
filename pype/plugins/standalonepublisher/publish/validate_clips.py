                # Check for clips with the same range
                # this is for testing if any vertically neighbouring
                # clips has been already processed
                clip_matching_with_range = next(
                    (k for k, v in context.data["assetsShared"].items()
                     if (v.get("_clipIn", 0) == clip_in)
                     and (v.get("_clipOut", 0) == clip_out)
                     ), False)

                # check if clip name is the same in matched
                # vertically neighbouring clip
                # if it is then it is correct and resent variable to False
                # not to be rised wrong name exception
                if asset in str(clip_matching_with_range):
                    clip_matching_with_range = False

                # rise wrong name exception if found one
                assert (not clip_matching_with_range), (
                    "matching clip: {asset}"
                    " timeline range ({clip_in}:{clip_out})"
                    " conflicting with {clip_matching_with_range}"
                    " >> rename any of clips to be the same as the other <<"
                ).format(
                    **locals())
