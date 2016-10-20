/*
 * lib_strbuf - library string storage
 */
#include <config.h>

#include <isc/net.h>

#include "ntp_fp.h"
#include "ntp_stdlib.h"
#include "lib_strbuf.h"


/*
 * Storage declarations
 */
int		debug;
libbufstr	lib_stringbuf[LIB_NUMBUF];
int		lib_nextbuf;


/*
 * initialization routine.  Might be needed if the code is ROMized.
 */
void
init_lib(void)
{
	static bool		lib_inited;

	if (lib_inited)
		return;
	init_systime();
	lib_inited = true;
}
