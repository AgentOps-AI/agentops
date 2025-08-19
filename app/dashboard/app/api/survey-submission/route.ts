import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();

        // Submit to external form service
        const externalFormPromise = fetch('https://submit-form.com/RQiLChq6c', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        }).catch(error => {
            console.error('External form submission error:', error);
            return { ok: false, error: error.message };
        });

        // Submit to HubSpot
        const hubspotData = new URLSearchParams();
        hubspotData.append('email', body.email || '');
        hubspotData.append('welcome_survey_usage_type', body.usage_type);
        hubspotData.append('welcome_survey_company_name', body.company_name);
        hubspotData.append('welcome_survey_company_size', body.company_size);
        hubspotData.append('welcome_survey_build_purpose', body.build_purpose);
        hubspotData.append('welcome_survey_stage', body.stage);
        hubspotData.append('welcome_survey_referral_source', body.referral_source);
        hubspotData.append('welcome_survey_other_referral', body.other_referral || '');
        hubspotData.append('welcome_survey_technologies', body.technologies?.join('; ') || '');
        hubspotData.append('welcome_survey_tools_used', body.tools_used || '');
        hubspotData.append('welcome_survey_help_needed', body.help_needed?.join('; ') || '');

        const hubspotPromise = fetch(
            'https://forms.hubspot.com/uploads/form/v2/48840765/8f7d568b-4504-45ac-87a8-9914947316f7',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: hubspotData.toString(),
            }
        ).catch(error => {
            console.error('HubSpot submission error:', error);
            return { ok: false, error: error.message };
        });

        // Wait for both submissions to complete
        const [externalFormResult, hubspotResult] = await Promise.allSettled([
            externalFormPromise,
            hubspotPromise,
        ]);

        // Log any errors but don't fail the request
        const errors = [];
        if (externalFormResult.status === 'rejected' || (externalFormResult.status === 'fulfilled' && !externalFormResult.value.ok)) {
            errors.push('External form submission failed');
        }
        if (hubspotResult.status === 'rejected' || (hubspotResult.status === 'fulfilled' && !hubspotResult.value.ok)) {
            errors.push('HubSpot submission failed');
        }

        return NextResponse.json({
            success: true,
            errors: errors.length > 0 ? errors : undefined
        });
    } catch (error: any) {
        console.error('[API Route /api/survey-submission] Error:', error);
        return new NextResponse(JSON.stringify({ error: 'Internal Server Error', details: error.message }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' },
        });
    }
} 