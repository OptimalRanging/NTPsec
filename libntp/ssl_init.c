/*
 * ssl_init.c	Common OpenSSL initialization code for the various
 *		programs which use it.
 *
 * Moved from ntpd/ntp_crypto.c crypto_setup()
 */
#ifdef HAVE_CONFIG_H
#include <config.h>
#endif
#include <ctype.h>
#include <ntp.h>
#include <ntp_debug.h>
#include <lib_strbuf.h>

#ifdef OPENSSL
#include "openssl/err.h"
#include "openssl/rand.h"


int ssl_init_done;

void
ssl_init(void)
{
	if (ssl_init_done)
		return;

	ERR_load_crypto_strings();
	OpenSSL_add_all_algorithms();

	ssl_init_done = 1;
}


void
ssl_check_version(void)
{
	if ((SSLeay() ^ OPENSSL_VERSION_NUMBER) & ~0xff0L) {
		msyslog(LOG_WARNING,
		    "OpenSSL version mismatch. Built against %lx, you have %lx",
		    OPENSSL_VERSION_NUMBER, SSLeay());
		fprintf(stderr,
		    "OpenSSL version mismatch. Built against %lx, you have %lx\n",
		    OPENSSL_VERSION_NUMBER, SSLeay());
	}

	INIT_SSL();
}
#endif	/* OPENSSL */


/*
 * keytype_from_text	returns OpenSSL NID for digest by name, and
 *			optionally the associated digest length.
 *
 * Used by ntpd authreadkeys(), ntpq and ntpdc keytype()
 */
int
keytype_from_text(
	const char *text,
	size_t *pdigest_len
	)
{
	int		key_type;
	u_int		digest_len;
#ifdef OPENSSL
	u_char		digest[EVP_MAX_MD_SIZE];
	char *		upcased;
	char *		pch;
	EVP_MD_CTX	ctx;

	/*
	 * OpenSSL digest short names are capitalized, so uppercase the
	 * digest name before passing to OBJ_sn2nid().  If it is not
	 * recognized but begins with 'M' use NID_md5 to be consistent
	 * with past behavior.
	 */
	INIT_SSL();
	LIB_GETBUF(upcased);
	strncpy(upcased, text, LIB_BUFLENGTH);
	for (pch = upcased; '\0' != *pch; pch++)
		*pch = (char)toupper(*pch);
	key_type = OBJ_sn2nid(upcased);
#else
	key_type = 0;
#endif

	if (!key_type && 'm' == tolower(text[0]))
		key_type = NID_md5;

	if (!key_type)
		return 0;

	if (NULL != pdigest_len) {
#ifdef OPENSSL
		u_int max_digest_len = 0;
		if (MAX_MAC_LEN > sizeof(keyid_t))
			max_digest_len = MAX_MAC_LEN - sizeof(keyid_t);

		EVP_DigestInit(&ctx, EVP_get_digestbynid(key_type));
		EVP_DigestFinal(&ctx, digest, &digest_len);
		if (digest_len > max_digest_len) {
			fprintf(stderr,
				"key type %s %u octet digests are too big, max %u\n",
				keytype_name(key_type), digest_len, max_digest_len);
			msyslog(LOG_ERR,
				"key type %s %u octet digests are too big, max %u",
				keytype_name(key_type), digest_len, max_digest_len);
			return 0;
		}
#else
		digest_len = 16;
#endif
		*pdigest_len = digest_len;
	}

	return key_type;
}


/*
 * keytype_name		returns OpenSSL short name for digest by NID.
 *
 * Used by ntpq and ntpdc keytype()
 */
const char *
keytype_name(
	int nid
	)
{
	static const char unknown_type[] = "(unknown key type)";
	const char *name;

#ifdef OPENSSL
	INIT_SSL();
	name = OBJ_nid2sn(nid);
	if (NULL == name)
		name = unknown_type;
#else	/* !OPENSSL follows */
	if (NID_md5 == nid)
		name = "MD5";
	else
		name = unknown_type;
#endif
	return name;
}

