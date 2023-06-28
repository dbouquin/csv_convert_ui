#%%
import os
import csv
import pandas as pd
import re
import requests # needed for USPS API
import xml.etree.ElementTree as ET # needed to parse USPS API returned XML

#%%
def modify_csv(file_path):
    # Generate the new file name
    new_file_path = os.path.splitext(file_path)[0]
    modified_file = new_file_path + "_modified.csv"
    exports_dir = os.path.join(os.path.dirname(file_path), "../exports")
    os.makedirs(exports_dir, exist_ok=True)
    modified_file_path = os.path.join(exports_dir, os.path.basename(modified_file))

    # Load CSV data into a DataFrame
    df = pd.read_csv(file_path, encoding='ISO-8859-1', low_memory=False)

    # make sure blanks are blank
    df = df.fillna('')

    # drop all rows that are completely blank
    df.dropna(how='all', inplace=True)

    # remove leading/trailing whitespace in all columns
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # drop prefix columns because we won't be using them
    df = df.drop(columns=['PREFIX', 'SPOUSEPREFIX'])

    # Remove any records containing the word "family"
    df = df[~df[['FIRSTNAME','LASTNAME', 'SUFFIX', 'SPOUSEFIRSTNAME','SPOUSELASTNAME', \
                 'SPOUSESUFFIX']].apply(lambda x: x.str.contains(' family|family |family', case=False)).any(axis=1)]

    # Remove any records containing the word "foundation"
    df = df[~df[['FIRSTNAME','LASTNAME', 'SUFFIX', 'SPOUSEFIRSTNAME','SPOUSELASTNAME', \
                 'SPOUSESUFFIX']].apply(lambda x: x.str.contains(' foundation|foundation |foundation', case=False)).any(axis=1)]
    #%% md
    ## Name Transformations
    # Split and restructure names to conform with iWave requirements
    #%%
    # mark the records that have two names
    # use regex to match "and" or "&"
    df['HAD_AND'] = df['FIRSTNAME'].apply(lambda x: bool(re.search(r'\band\b|&', x, flags=re.IGNORECASE)))
    #%%
    # define function to count characters and ignore periods

    def alpha_count(s):
        return sum(c.isalpha() for c in s.replace(".", ""))

    # define function to transform names

    def transform_name(row):
        # define regex pattern to match "and" or "&"
        pattern = re.compile(r"\band\b|&", flags=re.IGNORECASE)

        # split &/and names
        if pattern.search(row["FIRSTNAME"]):
            # Split the FIRSTNAME string on "&" or "and"
            name_parts = pattern.split(row["FIRSTNAME"])
            if len(name_parts) == 2:
                row["FIRSTNAME"] = name_parts[0].strip()
                row["SPOUSEFIRSTNAME"] = name_parts[1].strip()
            else:
                row["REVIEW"] = "N"
                return row

        # if either of the following two conditions are true, mark the row REVIEW = "N" and TRANSFORMED = "N":
        # 1. more than 1 character in FIRSTNAME and more than one character in LASTNAME
        # 2. 1 character in FIRSTNAME and more than one character in MIDDLENAME_INITIAL and more than one character in LASTNAME

        # check for valid names
        if (alpha_count(row["FIRSTNAME"]) > 1  and alpha_count(row["LASTNAME"]) > 1) or \
                (alpha_count(row["FIRSTNAME"]) == 1 and alpha_count(row["MIDDLENAME_INITIAL"]) > 1 and \
                 alpha_count(row["LASTNAME"]) > 1):
            row["REVIEW"] = "N"
            row["TRANSFORMED"] = "N"
            return row

        # check for valid names with spouse info
        elif (alpha_count(row["FIRSTNAME"]) <= 1 and alpha_count(row["MIDDLENAME_INITIAL"]) <= 1) and \
                ((alpha_count(row["SPOUSEFIRSTNAME"]) > 1 and alpha_count(row["SPOUSELASTNAME"]) > 1) or \
                 (alpha_count(row["SPOUSEFIRSTNAME"]) == 1 and alpha_count(row["SPOUSEMIDDLENAME_INITIAL"]) > 1 and \
                  alpha_count(row["SPOUSELASTNAME"]) > 1)):

            # store original name fields
            orig_firstname = row["FIRSTNAME"]
            orig_middlename = row["MIDDLENAME_INITIAL"]
            orig_lastname = row["LASTNAME"]
            orig_suffix = row["SUFFIX"]

            # switch name fields with spouse name fields
            row["FIRSTNAME"] = row["SPOUSEFIRSTNAME"]
            row["MIDDLENAME_INITIAL"] = row["SPOUSEMIDDLENAME_INITIAL"]
            row["LASTNAME"] = row["SPOUSELASTNAME"]
            row["SUFFIX"] = row["SPOUSESUFFIX"]

            # write original name fields into spouse name fields
            row["SPOUSEFIRSTNAME"] = orig_firstname
            row["SPOUSEMIDDLENAME_INITIAL"] = orig_middlename
            row["SPOUSELASTNAME"] = orig_lastname
            row["SPOUSESUFFIX"] = orig_suffix

            row["REVIEW"] = "N"
            row["TRANSFORMED"] = "Y"
            return row

        # check for invalid names
        elif (alpha_count(row["FIRSTNAME"]) <= 1 and alpha_count(row["MIDDLENAME_INITIAL"]) <= 1) or \
                (alpha_count(row["LASTNAME"]) <= 1):
            row["REVIEW"] = "Y"
            row["TRANSFORMED"] = "N"
            return row
    #%%
    # define a function to look for additional information in email addresses

    def check_email(row):
        if pd.isnull(row["EMAIL"]) or row["EMAIL"].strip() == "":
            row['CHECK_EMAIL'] = 'N'
            return row

        if row["REVIEW"]== "N":
            row['CHECK_EMAIL'] = 'N'
            return row

        # CHECK_EMAIL = "Y" if LASTNAME is part of the email address
        if row["LASTNAME"].lower() in row["EMAIL"].lower() and len(row["LASTNAME"]) > 1 or \
                row["SPOUSELASTNAME"].lower() in row["EMAIL"].lower() and len(row["SPOUSELASTNAME"]) > 1:
            row['CHECK_EMAIL'] = 'Y'
            return row
    #%%
    # define a function to convert initial first names to strings with spaces (e.g., T J instead of T.J.)
    # don't apply this to prefixes or suffixes
    pattern = re.compile(r'^\b(Mr|Ms|Mrs|Dr|Prof|Sr|Jr)\b', flags=re.IGNORECASE)

    def convert_initials(row):
        # apply only if there is more than one period
        if pd.notnull(row["FIRSTNAME"]) and row["FIRSTNAME"].count('.') > 1 and \
                not re.match(pattern, row["FIRSTNAME"]):
            row['TRANSFORMED'] = 'Y'
            row['FIRSTNAME'] = re.sub(r'\.', ' ', row["FIRSTNAME"])
        return row

    # trim white space again
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    #%%
    # Treat the name and ID columns as strings
    cols_to_convert = list(range(7))
    df.iloc[:, cols_to_convert] = df.iloc[:, cols_to_convert].astype(str)
    #%% md
    #**Run Functions**
    #%%
    # apply name transformations
    df = df.apply(transform_name, axis=1)
    #%%
    # apply email checker
    df = df.apply(check_email, axis=1)
    #%%
    # apply initial converter
    df = df.apply(convert_initials, axis=1)
    #%%
    # mark split names as TRANSFORMED
    # boolean indexing to mark rows as 'Y' when HAD_AND = True
    df.loc[df['HAD_AND'] == True, 'HAD_AND'] = 'Y'
    df.loc[df['HAD_AND'] == False, 'HAD_AND'] = 'N'
    #%%
    # mark records with suspected prefixes and suffixes hidden in FIRSTNAME
    df['PREFIX_SUSPECT'] = df['FIRSTNAME'].str.extract(r'\b(MR\.?|MS\.?|MRS\.?|DR\.?|REV\.?|PROF\.?)\b', \
                                                       flags=re.IGNORECASE, expand=False).notnull().map({True: 'Y', False: 'N'})
    df['SUFFIX_SUSPECT'] = df['FIRSTNAME'].str.extract(r'\b(JR\.?|SR\.?|II\.?|III\.?|IV\.?|V\.?)\b', \
                                                       flags=re.IGNORECASE, expand=False).notnull().map({True: 'Y', False: 'N'})

    prefix_suspects = df.loc[df['PREFIX_SUSPECT'] == 'Y']
    suffix_suspects = df.loc[df['SUFFIX_SUSPECT'] == 'Y']

    # mark prefix and suffix suspects for review
    df.loc[df['PREFIX_SUSPECT'] == 'Y', 'REVIEW'] = 'Y'
    df.loc[df['SUFFIX_SUSPECT'] == 'Y', 'REVIEW'] = 'Y'
    #%%
    # strip periods from name columns
    df['FIRSTNAME'] = df['FIRSTNAME'].str.replace('.', '')
    df['SPOUSEFIRSTNAME'] = df['SPOUSEFIRSTNAME'].str.replace('.', '')
    df['MIDDLENAME_INITIAL'] = df['MIDDLENAME_INITIAL'].str.replace('.', '')
    df['SUFFIX'] = df['SUFFIX'].str.replace('.', '')
    df['SPOUSEMIDDLENAME_INITIAL'] = df['SPOUSEMIDDLENAME_INITIAL'].str.replace('.', '')
    df['SPOUSESUFFIX'] = df['SPOUSESUFFIX'].str.replace('.', '')
    #%%
    # create fullname column
    df['FULLNAME'] = df['FIRSTNAME'].str.cat(df['MIDDLENAME_INITIAL'], \
                                             sep=' ', na_rep='').str.cat(df['LASTNAME'], \
                                                                         sep=' ', na_rep='').str.cat(df['SUFFIX'], sep=' ', na_rep='')
    #%%
    # create reference columns so Excel can sort on length of names
    df['FIRSTNAME_LEN'] = df['FIRSTNAME'].str.len()
    df['MIDDLE_LEN'] = df['MIDDLENAME_INITIAL'].str.len()
    df['LASTNAME_LEN'] = df['LASTNAME'].str.len()
    df['SPOUSE_FIRSTNAME_LEN'] = df['SPOUSEFIRSTNAME'].str.len()
    df['SPOUSE_MIDDLE_LEN'] = df['SPOUSEMIDDLENAME_INITIAL'].str.len()
    df['SPOUSELASTNAME_LEN'] = df['SPOUSELASTNAME'].str.len()
    #%% md
    ## Address Cleanup
    # Limit geographic scope and validate addresses using USPS API
    #%%
    # Keep only US
    df = df[df['COUNTRY'] == 'US']

    # Drop territories/APO addresses
    df = df[~df['STATE_PROVINCE'].isin(['VI', 'PR', 'GU', 'AS'])]

    # Create columns for checking address problems
    df['STATE_INVALID'] = 'N'
    df['ADDRESS_BLANK'] = 'N'
    df['ADDRESS_INCOMPLETE'] = 'N'

    # Replace "#" with "Unit"
    df["ADDRESS2"] = df["ADDRESS2"].str.replace("# ", "Unit ")
    df["ADDRESS2"] = df["ADDRESS2"].str.replace("#", "Unit ")
    #%%
    # define a set of valid US state and territory abbreviations
    us_states_abbrev = set(['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID',
                            'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO',
                            'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA',
                            'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'])

    # iterate through each row in the dataframe
    for i, row in df.iterrows():
        address_line1 = row['ADDRESS1'].strip().rstrip('.')
        address_line2 = row['ADDRESS2'].strip().rstrip('.')
        city = row['CITY'].strip()
        state = row['STATE_PROVINCE'].strip().upper()
        zipcode = row['ZIP_POSTALCODE'].strip()

        # check if all address columns are blank
        if address_line1 == '' and address_line2 == '' and city == '' and state == '' and zipcode == '':
            df.at[i, 'ADDRESS_BLANK'] = 'Y'
            df.at[i, 'STATE_INVALID'] = 'Y'  # Mark STATE_INVALID as 'Y' for blank addresses
            continue

        # validate the state abbreviation
        if pd.isnull(state) or state.strip() == '' or state.strip().upper() not in us_states_abbrev:
            df.at[i, 'STATE_INVALID'] = 'Y'
            df.at[i, 'ADDRESS_INCOMPLETE'] = 'Y'
        continue

        # check if any necessary address columns are blank
        if pd.isnull(address_line1) or address_line1 == '' or pd.isnull(zipcode) or zipcode == '' or \
                pd.isnull(state) or state == '':
            df.at[i, 'ADDRESS_INCOMPLETE'] = 'Y'
            continue

        # construct the full address
        full_address_parts = []
        if address_line1 != '':
            full_address_parts.append(address_line1)
        if address_line2 != '':
            full_address_parts.append(address_line2)
        if city != '':
            full_address_parts.append(city)
        if state != '':
            full_address_parts.append(state)
        if zipcode != '':
            full_address_parts.append(zipcode)

        # update the row with modified address values
        df.at[i, 'ADDRESS1'] = address_line1
        df.at[i, 'ADDRESS2'] = address_line2

        # join the address parts with commas
        df.at[i, 'FULL_ADDRESS'] = ', '.join(full_address_parts)

    # reset the value for ADDRESS_BLANK where ADDRESS_INCOMPLETE is marked
    df.loc[df['ADDRESS_INCOMPLETE'] == 'Y', 'ADDRESS_BLANK'] = 'N'

    # write blank addresses to their own df
    # if we need to check the blanks they're stored in blank_addresses
    blank_addresses = df.loc[df['ADDRESS_BLANK'] == "Y"]

    # drop all the records with blank addresses
    df = df[df['ADDRESS_BLANK'] != 'Y']

    # drop the ADDRESS_BLANK column (they all are "N" now)
    df = df.drop("ADDRESS_BLANK", axis=1)
    #%% md
    #USPS API
    #%%
    # define function to use USPS API to return validated addresses
    def validate_address(address1, address2, address3, city, zip_postalcode):
        api_url = "https://secure.shippingapis.com/ShippingAPI.dll"
        username = "3NATIO834I773"

        params = {
            "API": "Verify",
            "XML": f"<AddressValidateRequest USERID='{username}'>"
                   f"<Address ID='0'>"
                   f"<Address1>{address1}</Address1>"
                   f"<Address2>{address2}</Address2>"
                   f"<City>{city}</City>"
                   f"<State></State>"
                   f"<Zip5>{zip_postalcode}</Zip5>"
                   f"<Zip4></Zip4>"
                   f"</Address>"
                   f"</AddressValidateRequest>"
        }

        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            parsed_response = ET.fromstring(response.text)

            corrected_address_parts = {}
            corrected_address_parts["Address2"] = parsed_response.findtext(".//Address2")
            corrected_address_parts["Address3"] = address3
            corrected_address_parts["City"] = parsed_response.findtext(".//City")
            corrected_address_parts["State"] = parsed_response.findtext(".//State")
            corrected_address_parts["Zip5"] = parsed_response.findtext(".//Zip5")
            corrected_address_parts["Zip4"] = parsed_response.findtext(".//Zip4")

            # Create the "VALIDATION_ERROR" column and fill it with None
            result = pd.Series(corrected_address_parts, name="VALIDATION_ERROR")
            result["VALIDATION_ERROR"] = None

            error = parsed_response.find(".//Error")
            if error is not None:
                # Set the error message in the "VALIDATION_ERROR" column
                result["VALIDATION_ERROR"] = "Check original address for errors"

            return result

        except requests.exceptions.RequestException as e:
            print(f"Error occurred during address validation: {e}")
            # Create the "VALIDATION_ERROR" column and fill it with None
            result = pd.Series([None], name="VALIDATION_ERROR")
            result["VALIDATION_ERROR"] = None
            return result

    #%% md
    #**Execute address validation on the full dataset**
    #%%

    # Create a new dataframe to store the validated address parts
    validated_addresses = df.apply(
        lambda row: validate_address(
            row["FULLNAME"], row["ADDRESS1"], row["ADDRESS2"], row["CITY"], row["ZIP_POSTALCODE"]
        ),
        axis=1
    )

    # Rename the columns in the validated_addresses dataframe
    validated_addresses.columns = ["v_" + column for column in validated_addresses.columns]

    # Merge the validated addresses dataframe with the original dataframe
    df = pd.concat([df, validated_addresses], axis=1)

    # create combined zipcode column
    df["v_zipcode"] = df.apply(lambda row: f"{row['v_Zip5']}-{row['v_Zip4']}" if row['v_Zip5'] and \
                                                                                 row['v_Zip4'] else '', axis=1)

    # Drop columns that are no longer needed
    df = df.drop(columns=['STATE_INVALID', 'ADDRESS_INCOMPLETE'])

    # make sure blanks are blank
    df = df.fillna('')

    # cleanup columns
    # consistent capitalization
    df.columns = df.columns.str.upper()

    # incorporate apt/unit it into validated address
    df['V_STREET2'] = df['ADDRESS2'].str.upper()

    # make V_STREET2 blank when validation error occurs
    df.loc[df['V_VALIDATION_ERROR'] == 'Check original address for errors', 'V_STREET2'] = ''

    # mark validation errors for review
    df.loc[df['V_VALIDATION_ERROR'] == 'Check original address for errors', 'REVIEW'] = 'Y'

    # rename street address column to conform with original address column names
    df = df.rename({'V_ADDRESS2': 'V_STREET'}, axis=1)

    # reorder
    df = df[['ROI_ID', # household id
             'ROI_FAMILY_ID',            # individual id
             'FIRSTNAME',                # primary person info
             'MIDDLENAME_INITIAL',
             'LASTNAME',
             'SUFFIX',
             'FULLNAME',
             'MAIDEN',
             'NICKNAME',
             'TITLE',
             'AGE',
             'PHONE',
             'EMAIL',
             'SPOUSEFIRSTNAME',          # partner info
             'SPOUSEMIDDLENAME_INITIAL',
             'SPOUSELASTNAME',
             'SPOUSESUFFIX',
             'SPOUSEMAIDENNAME',
             'SPOUSENICKNAME',
             'REVIEW',                   # review names
             'TRANSFORMED',              # indicates that names were changed
             'CHECK_EMAIL',              # additional name info may be in email
             'PREFIX_SUSPECT',           # name may contain a prefix
             'SUFFIX_SUSPECT',           # name may contain a suffix
             'HAD_AND',                  # had two names combined in original dataset
             'V_VALIDATION_ERROR',
             'V_STREET',                 # valid address returned by the USPS API
             'V_STREET2',
             'V_CITY',
             'V_STATE',
             'V_ZIPCODE',
             'V_ZIP5',
             'V_ZIP4',
             'LARGESTGIFT',              # gift info
             'LARGESTGIFTDATE',
             'TOTALGIFTCOUNT',
             'TOTALGIFTAMOUNT',
             'LASTGIFTAMOUNT',
             'LASTGIFTDATE',
             'FIRSTGIFTAMOUNT',
             'FIRSTGIFTDATE',
             'ADDRESS1',                  # original address info
             'ADDRESS2',
             'LINE3',
             'LINE4',
             'CITY',
             'STATE_PROVINCE',
             'ZIP_POSTALCODE',
             'COUNTRY',
             'BUSINESS',
             'FIRSTNAME_LEN',              # name length columns
             'MIDDLE_LEN',
             'LASTNAME_LEN',
             'SPOUSE_FIRSTNAME_LEN',
             'SPOUSE_MIDDLE_LEN',
             'SPOUSELASTNAME_LEN']]

    # sort to make review easier
    df = df.sort_values(by=['REVIEW', 'CHECK_EMAIL', 'FIRSTNAME', 'MIDDLENAME_INITIAL', 'LASTNAME'],
                        ascending=[False, False, True, True, True])

    #%%
    # Save the modified DataFrame to a new CSV file
    df.to_csv(modified_file_path, index=False)

    return modified_file_path